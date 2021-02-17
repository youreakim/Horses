from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from germany.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

from scrapy_splash import SplashRequest

import datetime
import os
import calendar

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/germany'
BASE_URL = 'https://www.hvtonline.de/'
CALENDAR_URL = BASE_URL + 'monatsrennberichte/{}/'


class ResultcollectorSpider(Spider):
    """
    Collects results from 'https://www.hvtonline.de'.
    Takes a start_date and an end_date, these default to yesterday.
    """
    name = 'resultcollector'
    allowed_domains = ['hvtonline.de']


    def __init__(self, start_date = '', end_date = '', *args, **kwargs):
        super(ResultcollectorSpider, self).__init__(*args, **kwargs)
        yesterday = datetime.date.today() - datetime.timedelta(days = 1)
        self.start_date = datetime.date(*[int(x) for x in start_date.split('-')]) if start_date != '' else yesterday
        self.end_date = datetime.date(*[int(x) for x in end_date.split('-')]) if end_date != '' else yesterday


    def start_requests(self):
        while self.start_date <= self.end_date:
            yield SplashRequest(
                        url=CALENDAR_URL.format(self.start_date.strftime('%Y%m')),
                        callback=self.parse,
                        meta={'start_date': self.start_date,
                              'end_date': self.end_date})

            # Skip forward to next month
            self.start_date = self.start_date.replace(day = 1)
            self.start_date += datetime.timedelta(
                days = calendar.monthrange(self.start_date.year, self.start_date.month)[1])


    def parse(self, response):
        start_date = response.meta['start_date']
        end_date = response.meta['end_date']

        for raceday_link in response.xpath('//table[@class="rboverview"]//a'):
            raceday = ItemLoader(item = RacedayItem(), selector=raceday_link)

            raceday.add_xpath('date', './@href')
            raceday.add_xpath('racetrack', '.')
            raceday.add_xpath('racetrack_code', './@href')
            raceday.add_xpath('link', './@href')
            raceday.add_value('collection_date', datetime.date.today())
            raceday.add_value('status', 'result')

            filename = '_'.join([raceday.get_output_value('date').replace('-', '_'),
                                raceday.get_output_value('racetrack_code')]) + '.json'

            raceday_date = datetime.date(*[int(x) for x in raceday.get_output_value('date').split('-')])

            if (not os.path.exists(os.path.join(JSON_DIRECTORY, 'result', filename)) and
                response.meta['start_date'] <= raceday_date <= response.meta['end_date']):
                yield SplashRequest(
                            url=BASE_URL + raceday.get_output_value('link'),
                            callback=self.parse_raceday,
                            cb_kwargs=dict(raceday=raceday))


    def parse_raceday(self, response, raceday):
        race_links = response.xpath('//div[@class="rbleftcol"]//a[contains(@href,"https:")]/@href').getall()

        yield SplashRequest(
                    url=race_links[0],
                    callback=self.parse_race,
                    cb_kwargs=dict(raceday=raceday),
                    meta={'race_links': race_links})


    def parse_race(self, response, raceday):
        race_links = response.meta['race_links']
        race_link = race_links.pop(0)

        race = ItemLoader(item = RaceItem(), selector=response.xpath('//div[@id="fullwidth"]'))

        race.add_value('link', race_link)
        race.add_xpath('racenumber', './/h3[@class="gradient_1"]')
        race.add_xpath('racetype', './/h3[@class="gradient_1"]')

        race.add_xpath('racename', './/h3[@class="fulltext"]')
        race.add_xpath('conditions', './/li[@class="mittelinks"]')
        race.add_xpath('distance', './/li[@class="mitterechts"]')
        race.add_xpath('startmethod', './/li[@class="mitterechts"]')

        if race.get_output_value('racetype') == 'race':
            race.add_xpath('purse', './/li[@class="mittegesamt"]')

            starter_purse = response.xpath('//li[@class="mittegesamt"]').get()
            starter_purse = starter_purse[ starter_purse.find('(') + 1 : starter_purse.find(')') ].split(' · ')
            starter_purse = [int(x) for x in starter_purse]

            places = response.xpath('//td[text()="Place: " or text()="Platz: "]//following-sibling::td/text()').get()

            starter_places = []

            if places:
                starter_places = [x for x in places[ : places.find(":") ].split('-') if x != '']

        starters = []
        order = 0

        for index, row in enumerate(response.xpath('//table[@class="rbfull"]/tbody/tr'), 1):
            if index % 3 == 1:
                order += 1

            elif index % 3 == 2:
                starter = ItemLoader(item = RaceStarterItem(), selector=row)

                starter.add_xpath('finish', './td[1]')
                starter.add_xpath('driver', './td[3]')
                starter.add_xpath('trainer', './td[4]')
                starter.add_xpath('distance', './td[6]')
                starter.add_xpath('racetime', './td[7]')
                starter.add_xpath('disqualified', './td[7]')

                if starter.get_output_value('disqualified'):
                    starter.add_xpath('disqstring', './td[7]')

                if race.get_output_value('racetype') == 'race':
                    starter.add_xpath('ev_odds', './td[8]')

                    if starter.get_output_value('finish') == 1:
                        starter.add_value('odds', './td[8]')

                    if not starter.get_output_value('disqualified') and order <= len(starter_purse):
                        starter.add_value('purse', starter_purse[ order - 1 ])

                    if order <= len(starter_places):
                        starter.add_value('show_odds', starter_places[ order - 1 ])

                else:
                    starter.add_value('approved', True if starter.get_output_value('racetime') else False)

                starter.add_value('order', order)
                starter.add_value('started', True)

                horse = ItemLoader(item = HorseItem(), selector=row.xpath('./td[2]'))

                horse.add_xpath('name', '.')
                horse.add_xpath('country', '.')

            else:
                pedigree = row.xpath('./td[1]/text()').get()

                age = int(pedigree[ : pedigree.find('j.')])
                birthyear = int(raceday.get_output_value('date')[ 0 : 4 ]) - age

                horse.add_value('birthdate', '{}-01-01'.format(birthyear))
                horse.add_value('sex', pedigree[ pedigree.find('. v. ') - 1 : pedigree.find('. v. ') ])

                sire = ItemLoader(item = HorseItem())

                sire.add_value('name', pedigree[ pedigree.find('. v. ') + 5 : pedigree.find(' a. d. ') ])
                sire.add_value('sex', 'horse')

                horse.add_value('sire', dict(sire.load_item()))

                dam = ItemLoader(item = HorseItem())

                dam.add_value('name', pedigree[ pedigree.find(' a. d. ') + 7 : ])
                dam.add_value('sex', 'mare')

                horse.add_value('dam', dict(dam.load_item()))

                horse.add_value('breeder', row.xpath('./td[3]/text()').get())

                starter.add_value('horse', dict(horse.load_item()))

                race.add_value('starters', starter.load_item())

        scratched = response.xpath('//td[text()="Nichtstarter:"]//following-sibling::td/text()').get()

        if scratched is not None and scratched != '--':
            scratched = scratched.split(',')

            for scratch in scratched:
                starter = ItemLoader(item=RaceStarterItem())

                if scratch.startswith('Nr. '):
                    starter.add_value('startnumber',
                        scratch[ scratch.find('.') + 2 : scratch.find('.') + 5 ])

                    scratch = scratch[ scratch.find(' ', scratch.find('. ') + 2) : ]

                starter.add_value('started', False)
                starter.add_value('order', order)

                order += 1

                horse = ItemLoader(item=HorseItem())

                horse.add_value('name', scratch)
                horse.add_value('country', scratch)

                starter.add_value('horse', horse.load_item())

                race.add_value('starters', starter.load_item())

        race.add_value('starters', [x.load_item() for x in starters])

        raceday.add_value('races', race.load_item())

        if len(race_links) == 0:
            yield raceday.load_item()

        else:
            yield SplashRequest(
                        url=race_links[0],
                        callback=self.parse_race,
                        cb_kwargs=dict(raceday=raceday),
                        meta={'race_links': race_links})
