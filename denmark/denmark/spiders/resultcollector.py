from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from scrapy.selector import Selector
from denmark.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

from scrapy_splash import SplashFormRequest, SplashRequest

import os
import calendar

from base64 import b64decode
from datetime import date, datetime, timedelta

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/denmark'
BASE_URL = 'http://195.198.34.45'
CALENDAR_URL = BASE_URL + '/trav/lobsdagsresultater'


class ResultcollectorSpider(Spider):
    """
    Collects results from DTCs site.
    Takes a start_date and an end_date in the form 'yyyy-mm-dd', these default to yesterday.
    """
    name = 'resultcollector'
    allowed_domains = ['195.198.34.45']


    def __init__(self, start_date = '', end_date = '', *args, **kwargs):
        super(ResultcollectorSpider, self).__init__(*args, **kwargs)
        self.today = date.today()
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date != '' else self.today - timedelta(days = 1)
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date != '' else self.today - timedelta(days = 1)


    def start_requests(self):
        """
        Loop through all months between start_date and end_date, submit the form
        if it is not the current year and month. Collect all links, check if the
        date is in range, follow that link, record where it redirects to. Returns
        a list of lists, each containing the response url, racetrack name and
        the day of the month.
        I did not want this function to do too much, so there is some overhead.
        """
        lua_source = """
                    treat = require('treat')
                    function main(splash, args)
                      list = {}
                      day_list = {}
                      url = "http://195.198.34.45/trav"
                      assert(splash:go(args.url))
                      assert(splash:wait(0.5))
                      if args.year ~= "" and args.month ~= "" then
                        form = splash:select('div#content form')
                        form_id = form:getAttribute('id')
                        form_action = form:getAttribute('action')
                        action_url = url .. string.sub(form_action, 2)
                        body = form_id .. '_hf_0=&track=0&year=' .. args.year .. '&month=' .. args.month
                        splash:go{url=action_url, http_method="POST", body=body}
                        assert(splash:wait(3))
                      end
                      days = splash:select_all('table.calendar tbody td.calendar_column')
                      for row, day in ipairs(days) do
                        if row >= args.first and row <= args.last then
                            links = day:querySelectorAll('a')
                            for _, link in ipairs(links) do
                                l = string.sub(link:getAttribute('href'), 2)
                                t = link:querySelector('strong').textContent
                                day_list[#day_list + 1] = {url..l, t, row}
                            end
                        end
                      end
                      for ix, link in ipairs(day_list) do
                        local resp = splash:http_get(link[1])
                        assert(splash:wait(2))
                        list[#list + 1] = treat.as_array({resp.url, link[2], link[3]})
                      end
                      return treat.as_array(list)
                    end
                    """

        current_date = self.start_date

        while current_date <= self.end_date:
            year_value = ''
            month_value = ''
            first = 1
            last = self.end_date.day

            if current_date.year != self.today.year or current_date.month != self.today.month:
                # the value of the year to select in the form, 0 is 1995
                year_value = str(current_date.year - 1995)
                month_value = str(current_date.month - 1)

            if current_date.month == self.start_date.month and current_date.year == self.start_date.year:
                first = self.start_date.day

            if current_date.month != self.end_date.month or current_date.year != self.end_date.year:
                last = calendar.monthrange(current_date.year, current_date.month)[1]


            yield SplashRequest(
                        url=CALENDAR_URL,
                        callback=self.parse,
                        endpoint='execute',
                        meta={'date': current_date},
                        args={'wait': 5,
                              'year': year_value,
                              'month': month_value,
                              'first': first,
                              'last': last,
                              'lua_source': lua_source}
            )

            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year+1, month=1, day=1)
            else:
                current_date = current_date.replace(month=current_date.month+1, day=1)


    def parse(self, response):
        """
        Gets the page for the raceday, clicks on the tab for each race. Returns
        a har archive.
        """
        lua_source = """
                     function main(splash, args)
                        splash.response_body_enabled = true
                        splash:go(args.url)
                        assert(splash:wait(2))
                        local tabs = splash:select_all('ul.tab a.large')
                        local count = 2
                        while count <= #tabs do
                            tabs[count]:mouse_click()
                            assert(splash:wait(2))
                            tabs = splash:select_all('ul.tab a.large')
                            count = count + 1
                        end
                        return splash:har()
                     end
                     """

        for rd in response.data:
            raceday = ItemLoader(item=RacedayItem())

            raceday.add_value('racetrack', rd[1])
            raceday.add_value('status', 'result')
            raceday.add_value('link', rd[0])
            raceday.add_value('date', response.meta['date'].replace(day=rd[2]).strftime('%Y-%m-%d'))
            raceday.add_value('collection_date', self.today.strftime('%Y-%m-%d'))

            filename = '_'.join([raceday.get_output_value('date').replace('-', '_'),
                                rd[1].lower().replace(' ', '_')]) + '.json'

            if not os.path.exists(os.path.join(JSON_DIRECTORY, 'result', filename)):
                yield SplashRequest(
                            url=rd[0],
                            callback=self.parse_raceday,
                            cb_kwargs=dict(raceday=raceday),
                            endpoint='execute',
                            args={'wait': 5,
                                  'lua_source': lua_source}
                )


    def parse_raceday(self, response, raceday):
        for entry in response.data['log']['entries']:
            race_text = b64decode(entry['response']['content'].get('text', '')).decode('utf-8').strip()

            if len(race_text) > 0:
                if race_text.startswith('<?xml'):
                    race_text = race_text[ race_text.find('![CDATA[') + 8 : race_text.find(']]') ]

                race_selector = Selector(text=race_text)

                race = ItemLoader(item=RaceItem(), selector=race_selector)

                race.add_xpath('racetype', '//a[contains(@class,"selected")]')
                race.add_xpath('racenumber', '//h2[contains(text(),"Løb")]')
                race.add_xpath('purse', '//td[contains(text(),"Præmier:")]')
                race.add_xpath('racename', '//table[@class="info_text"]//td[1]/b')
                race.add_xpath('distance', '//td[contains(text()," m. ")]')
                race.add_xpath('startmethod', '//td[contains(text()," m. ")]')
                race.add_xpath('conditions', '//table[@class="info_text"]//td')

                if 'loppId' in entry['response']['url']:
                    race.add_value('link', entry['response']['url'])

                starter_rows = race_selector.xpath('//div[@class="clear"]//table[@class="latte"]//tr')[ 1: ]

                order = 1

                for starter_row in starter_rows:
                    starter = ItemLoader(item=RaceStarterItem(), selector=starter_row)

                    starter.add_value('order', order)
                    starter.add_value('started', True)

                    starter.add_xpath('disqualified', './td[1]')
                    starter.add_xpath('startnumber', './td[2]/span[1]')
                    starter.add_xpath('driver', './td[2]/div//span[1]')
                    starter.add_xpath('trainer', './td[2]/div//span[2]')
                    starter.add_xpath('postposition', './td[3]')
                    starter.add_xpath('distance', './td[3]')

                    if race.get_output_value('racetype') == 'race':
                        starter.add_xpath('finish', './td[1]')
                        starter.add_xpath('ev_odds', './td[5]')
                        starter.add_xpath('odds', './td[5]')
                        starter.add_xpath('show_odds', './td[6]')

                    else:
                        starter.add_xpath('approved', './td[5]')

                    starter.add_xpath('racetime', './td[7]')
                    starter.add_xpath('gallop', './td[7]')
                    starter.add_xpath('finished', './td[7]')

                    if starter.get_output_value('disqualified'):
                        starter.add_xpath('disqstring', './td[7]')

                    horse = ItemLoader(item=HorseItem(), selector=starter_row.xpath('./td[2]/a[1]'))

                    horse.add_xpath('name', '.')
                    horse.add_xpath('country', '.')
                    horse.add_xpath('link', './@href')

                    starter.add_value('horse', horse.load_item())

                    race.add_value('starters', starter.load_item())

                    order += 1

                scratches = race_selector.xpath('//'.join([
                    'table[contains(@class,"latte_tight")]',
                    'span[text()="Udgået: "]',
                    'ancestor::td',
                    'following-sibling::td',
                    'li']))

                for scratched in scratches:
                    starter = ItemLoader(item=RaceStarterItem(), selector=scratched)

                    starter.add_value('started', False)
                    starter.add_value('order', order)

                    starter.add_xpath('startnumber', './span')

                    horse = ItemLoader(item=HorseItem(), selector=scratched)

                    horse.add_xpath('name', './a')
                    horse.add_xpath('country', './a')
                    horse.add_xpath('link', './a/@href')

                    starter.add_value('horse', horse.load_item())

                    race.add_value('starters', starter.load_item())

                    order += 1

                raceday.add_value('races', race.load_item())

        yield raceday.load_item()
