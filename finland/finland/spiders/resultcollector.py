from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from finland.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

from scrapy_splash import SplashFormRequest, SplashRequest

import datetime
import re
import os


JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/finland'
BASE_URL = 'http://heppa.hippos.fi'
RACEDAY_URL = BASE_URL + '/heppa/app?page=racing%2FRaceResults&service=external&sp={}'
RACE_URL = BASE_URL + '/heppa/app?page=racing%2FRaceResults&service=external&sp={}'


class ResultcollectorSpider(Spider):
    """
    Collects results from 'https://heppa.hippos.fi/heppa/racing/RaceCalendar.html'.
    By default start_date and end_date is set to yesterday, provide date in the
    form of 'YYYY-MM-DD' to override.
    Looks for available results, checks if they are already collected, if not
    gets them, removing any pony races.
    Gets one race at the time, all races are available in the last tab on the raceday
    page, easier but more time consuming doing it this way.
    """
    name = 'resultcollector'
    allowed_domains = ['hippos.fi']


    def __init__(self, start_date = '', end_date = '', *args, **kwargs):
        super(ResultcollectorSpider, self).__init__(*args, **kwargs)
        yesterday = datetime.datetime.today() - datetime.timedelta(days = 1)
        self.start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d') if start_date != '' else yesterday
        self.end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d') if end_date != '' else yesterday


    def start_requests(self):
        lua_source = """
                    function main(splash, args)
                        local base = 'http://heppa.hippos.fi'
                        local function search_for_splash()
                            local form = splash:select('#form')
                            local startdate = splash:select('#dateRangeStart')
                            local enddate = splash:select('#dateRangeEnd')

                            assert(startdate:send_keys(args.start_date))
                            assert(enddate:send_keys(args.end_date))
                            assert(splash:wait(0))
                            assert(form:submit())
                        end

                        assert(splash:go(args.url))
                        assert(splash:wait(1))
                        search_for_splash()
                        assert(splash:wait(5))

                        return splash:html()
                    end
                    """

        url = BASE_URL + '/heppa/app?page=racing%2FRaceCalendarSearch&service=external'

        yield SplashRequest(url=url,
                            callback=self.parse,
                            endpoint='execute',
                            args={'lua_source': lua_source,
                                    'start_date': self.start_date.strftime('%d.%m.%Y'),
                                    'end_date': self.end_date.strftime('%d.%m.%Y')})


    def parse(self, response):
        rows = response.xpath('//table[@class="sortable"]/tbody/tr')

        for row in rows:
            raceday = ItemLoader(item = RacedayItem(), selector=row)

            raceday.add_xpath('date', './td[1]')
            raceday.add_xpath('racetrack', './td[3]')

            if not row.xpath('.//a'):
                raceday.add_value('status', 'cancelled')

                yield raceday.load_item()
                continue

            raceday.add_xpath('link', './/a/@href')
            raceday.add_xpath('racetrack_code', './/a/@href')

            raceday.add_value('collection_date', datetime.date.today().strftime('%Y-%m-%d'))
            raceday.add_value('status', 'result')

            filename        = '_'.join([
                raceday.get_output_value('date').replace('-', '_'),
                raceday.get_output_value('racetrack_code').lower()]) + '.json'

            if not os.path.exists(os.path.join(JSON_DIRECTORY, 'result', filename)):
                yield SplashRequest(
                    url=RACEDAY_URL.format(raceday.get_output_value('link')),
                    callback=self.parse_raceday,
                    cb_kwargs=dict(raceday=raceday))


    def parse_raceday(self, response, raceday):
        racelinks = response.xpath('//a[contains(text(),"lähtö") and not(contains(text(),"ponilähtö"))]/@href').getall()

        if len(racelinks) != 0:
            yield SplashRequest(
                url=BASE_URL + racelinks.pop(0),
                callback=self.parse_race,
                cb_kwargs=dict(raceday=raceday),
                meta={
                    'racelinks': racelinks
                }
            )


    def parse_race(self, response, raceday):
        race = ItemLoader(item=RaceItem(), selector=response.xpath('//div[@class="full_column"][1]'))

        race.add_value('link', response.url)
        race.add_value('racenumber', response.url)

        race.add_xpath('conditions', './/h3')
        race.add_xpath('distance', './/h3')
        race.add_xpath('purse', './/h3')
        race.add_xpath('monte', './/h3')
        race.add_xpath('startmethod', './/h3')
        race.add_xpath('racetype', './/h3')

        if race.get_output_value('racetype') == 'race':
            # if two or more horses dead heat, the odds will be separated by '/'
            # instead of '-'
            win_odds = response.xpath('//td[text()="Voittaja"]//following-sibling::td/text()').get()
            win_odds = win_odds.strip().replace('/', '-').split('-')

            show_odds = response.xpath('//td[text()="Sija"]//following-sibling::td/text()').get()
            show_odds = show_odds.strip().replace('/', '-').split('-')

        starter_rows = response.xpath('//table[@class="raceResultTable"]//tr')[1:]

        for order, starter_row in enumerate(starter_rows, 1):
            starter = ItemLoader(item=RaceStarterItem(), selector=starter_row)

            starter.add_value('order', order)

            starter.add_xpath('finish', './td[1]')
            starter.add_xpath('startnumber', './td[2]')

            horse = ItemLoader(item=HorseItem(), selector=starter_row.xpath('.//a[1]'))

            horse.add_xpath('name', '.')
            horse.add_xpath('link', './@href')

            starter.add_value('horse', horse.load_item())

            starter.add_xpath('driver', './/a[2]')
            starter.add_xpath('distance', './td[8]')
            starter.add_xpath('postposition', './td[8]')

            if starter_row.xpath('./td[contains(text(),"Poissa")]'):
                starter.add_value('started', False)
            else:
                starter.add_value('started', True)
                starter.add_xpath('racetime', './td[4]')

                # I haven't contacted Hippos to find out what all the codes in the fifth 
                # column mean, an 'x' denotes that the horse had made a break
                starter.add_xpath('disqstring', './td[5]')
                starter.add_xpath('gallop', './td[5]')

                starter.add_xpath('ev_odds', './td[6]')
                starter.add_xpath('purse', './td[7]')

                if race.get_output_value('racetype') == 'race':
                    if order <= len(win_odds):
                        starter.add_value('odds', win_odds[order - 1])

                    if order <= len(show_odds):
                        starter.add_value('show_odds', show_odds[order - 1])

            race.add_value('starters', starter.load_item())

        raceday.add_value('races', race.load_item())

        if len(response.meta['racelinks']) == 0:
            yield raceday.load_item()

        else:
            yield SplashRequest(
                url=BASE_URL + response.meta['racelinks'].pop(0),
                callback=self.parse_race,
                cb_kwargs=dict(raceday=raceday),
                meta={
                    'racelinks': response.meta['racelinks']
                }
            )
