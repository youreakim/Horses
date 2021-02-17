from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from germany.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

from scrapy_splash import SplashRequest

import datetime
import os


JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/germany'
BASE_URL = 'https://www.hvtonline.de/'


class StartlistcollectorSpider(Spider):
    """
    Collects startlists from 'https://www.hvtonline.de'
    """
    name = 'startlistcollector'
    allowed_domains = ['hvtonline.de']


    def start_requests(self):
        yield SplashRequest(
                    url=BASE_URL,
                    callback=self.parse)


    def parse(self, response):
        for raceday_link in response.xpath('//p[@class="historyitem"]/a[contains(@href,"starter")]'):
            raceday = ItemLoader(item = RacedayItem(), selector=raceday_link)

            raceday.add_xpath('date', './@href')
            raceday.add_xpath('racetrack', '.')
            raceday.add_xpath('racetrack_code', './@href')
            raceday.add_xpath('link', './@href')
            raceday.add_value('collection_date', datetime.datetime.today())
            raceday.add_value('status', 'startlist')

            filename = '_'.join([raceday.get_output_value('date').replace('-', '_'),
                                raceday.get_output_value('racetrack_code')]) + '.json'

            if not os.path.exists(os.path.join(JSON_DIRECTORY, 'startlist', filename)):
                yield SplashRequest(
                            url=BASE_URL + raceday.get_output_value('link'),
                            callback=self.parse_raceday,
                            cb_kwargs=dict(raceday=raceday))


    def parse_raceday(self, response, raceday):
        # The only information we're interested in here is the links, this page
        # does contain basic startlists, there is more information in the pages
        # for each race.
        race_links = response.xpath('//div[@class="rightcol"]//a/@href').getall()

        yield SplashRequest(
                    url=race_links[0],
                    callback=self.parse_race,
                    cb_kwargs=dict(raceday=raceday),
                    meta={'race_links': race_links})


    def parse_race(self, response, raceday):
        race_links = response.meta['race_links']
        race_link = race_links.pop(0)

        race = ItemLoader(item=RaceItem(), selector=response.xpath('//div[@id="raceheaderleft"]'))

        race.add_value('link', race_link)
        race.add_xpath('racenumber', './/h3[@class="gradient_1"]')
        race.add_xpath('racetype', './/h3[@class="gradient_1"]')
        race.add_xpath('racename', './/h3[@class="fulltext"]')

        conditions = response.xpath('//div[@class="racetitleright"]//li//text()').getall()[ : 3 ]
        race.add_value('conditions', conditions)

        race.add_xpath('distance', './/li[@class="mitterechts"][2]')
        race.add_xpath('startmethod', './/li[@class="mitterechts"][2]')

        distance = str(race.get_output_value('distance'))
        postposition = 1

        for row in response.xpath('//div[@id="cardshort"]/div'):
            # if the race use the standing startmethod the first horse at each distance
            # is preceded by two divs, one that contains the distance and one empty
            if row.xpath('./@class').get() == 'band':
                distance = row.xpath('.//text()').get()
                postposition = 1
                continue

            elif not row.xpath('./@class').get():
                continue

            starter = ItemLoader(item = RaceStarterItem(), selector=row)

            starter.add_xpath('startnumber', './/div[@class="startnummer"]')
            starter.add_value('postposition', postposition)
            starter.add_xpath('driver', './/p[@class="row2"]')
            starter.add_xpath('trainer', './/p[@class="row4"]')
            starter.add_value('distance', distance)

            horse = ItemLoader(item = HorseItem(), selector=row.xpath('.//p[@class="row1"]/a'))

            horse.add_xpath('name', '.')
            horse.add_xpath('country', '.')
            horse.add_xpath('link', './@data-horseid')
            horse.add_value('breeder', row.xpath('.//span[@class="item3"]/text()').get())

            age_info = row.xpath('.//td[@class="abstammung"]/text()').get()
            birthyear = int(raceday.get_output_value('date')[ : 4 ]) - int(age_info[ : age_info.find('j') ])

            horse.add_value('birthdate', str(birthyear))
            horse.add_value('sex', age_info[ age_info.find('. v. ') - 1 : age_info.find('. v. ') ])

            sire = ItemLoader(item = HorseItem())

            sire_name = age_info[ age_info.find('. v. ') + 5 : age_info.find(' a. d. ') ].strip()

            if '(' in sire_name:
                sire.add_value('country', sire_name)

            sire.add_value('name', sire_name)
            sire.add_value('sex', 'horse')

            horse.add_value('sire', sire.load_item())

            dam = ItemLoader(item = HorseItem())

            dam_name = age_info[ age_info.find(' a. d. ') + 7 : ].strip()

            if '(' in dam_name:
                dam.add_value('country', dam_name)

            dam.add_value('name', dam_name)
            dam.add_value('sex', 'mare')

            horse.add_value('dam', dam.load_item())

            starter.add_value('horse', horse.load_item())

            race.add_value('starters', starter.load_item())

            postposition += 1

        raceday.add_value('races', race.load_item())

        if len(race_links) == 0:
            yield raceday.load_item()

        else:
            yield SplashRequest(
                        url=race_links[0],
                        callback=self.parse_race,
                        cb_kwargs=dict(raceday=raceday),
                        meta = {'race_links': race_links})
