from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from scrapy_splash import SplashRequest
from w3lib.html import remove_tags

from finland.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

import datetime
import os


JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/finland'
BASE_URL = 'https://heppa.hippos.fi'
START_URL = f'{BASE_URL}/heppa/racing/RaceCalendar.html'
RACEDAY_URL = BASE_URL + '/heppa/app?page=racing%2FRaceProgramMain&service=external&sp={}'
RACE_URL = BASE_URL + '/heppa/app?page=racing%2FRaceProgramOneRace&service=external&sp={}'


class StartlistcollectorSpider(Spider):
    """
    Collects startlists from 'https://heppa.hippos.fi/heppa/racing/RaceCalendar.html'
    Looks for available startlists, checks if they are already collected, if not
    gets them, removing any pony races.
    """
    name = 'startlistcollector'
    allowed_domains = ['hippos.fi']


    def start_requests(self):
        yield SplashRequest(url=START_URL,
                            callback=self.parse_calendar)


    def parse_calendar(self, response):
        rows = response.xpath('//span[@class="program_icon"]//ancestor::tr')

        for row in rows:
            raceday = ItemLoader(item=RacedayItem(), selector=row)

            raceday.add_xpath('date', './td[1]')
            raceday.add_xpath('racetrack', './td[3]/a')
            raceday.add_xpath('link', './td[7]/a/@href')
            raceday.add_xpath('racetrack_code', './td[7]/a/@href')

            raceday.add_value('collection_date', datetime.date.today().strftime('%Y-%m-%d'))
            raceday.add_value('status', 'startlist')

            filename = '_'.join([
                raceday.get_output_value('date').replace('-', '_'),
                raceday.get_output_value('racetrack_code').lower()]) + '.json'

            if not os.path.exists(os.path.join(JSON_DIRECTORY, 'startlist', filename)):
                yield SplashRequest(url=RACEDAY_URL.format(raceday.get_output_value("link")),
                                    callback=self.parse_day,
                                    cb_kwargs=dict(raceday=raceday))


    def parse_day(self, response, raceday):
        races = []

        # we do not want pony races, if it's just pony races we will get no races
        # and this day will be skipped
        for row in response.xpath('//a[contains(text(),"lähtö") and not(contains(text(),"ponilähtö"))]'):
            race = ItemLoader(item = RaceItem(), selector=row)

            race.add_xpath('link', './@href')
            race.add_xpath('racenumber', './@href')
            race.add_xpath('racetype', '.')
            race.add_xpath('monte', '.')
            race.add_xpath('startmethod', '.')
            race.add_xpath('distance', '.')
            race.add_xpath('conditions', '.')
            race.add_xpath('purse', '.')

            race.add_value('status', 'startlist')

            races.append(race)

        if len(races) != 0:
            yield SplashRequest(url=RACE_URL.format(races[0].get_output_value('link')),
                                callback=self.parse_race,
                                cb_kwargs=dict(raceday=raceday),
                                meta = {'races': races})


    def parse_race(self, response, raceday):
        races = response.meta['races']

        race = races.pop(0)

        starters = []

        rows = response.xpath('//table[@class="race_program"]//tr')[ : -1]
        rows = [rows[ i : i + 11 ] for i in range(0, len(rows), 11)]

        distance = race.get_output_value('distance')

        for row in rows:
            starter = ItemLoader(item = RaceStarterItem())

            starter.add_value('startnumber', row[1].xpath('.//td[1]').get())

            dist_post = remove_tags(row[2].xpath('.//td[2]/h2').get())

            # only the first horse that starts at the distance will have both
            # the distance and the postposition
            if ':' in dist_post:
                starter.add_value('distance', dist_post)
                starter.add_value('postposition', dist_post)

                distance = str(starter.get_output_value('distance'))

            else:
                starter.add_value('distance', distance)
                starter.add_value('postposition', dist_post)

            starter.add_value('driver', row[8].xpath('.//td[1]/a//text()').get())

            if row[7].xpath('.//td[1]/a'):
                starter.add_value('trainer', row[7].xpath('.//td[1]/a//text()').get())
            else:
                starter.add_value('trainer', starter.get_output_value('driver'))

            if row[2].xpath('.//td[1]/h2/a/@class') == 'racefield_horse_absence':
                starter.add_value('started', False)

            horse = ItemLoader(item = HorseItem(), selector=row[2])

            horse.add_xpath('name', './/a')
            horse.add_xpath('country', './/a')
            horse.add_xpath('link', './/a/@href')

            birthyear = row[3].xpath('.//td[1]/text()').get().strip()
            birthyear = int(raceday.get_output_value('date')[ : 4 ]) - int(birthyear[ : birthyear.find(' ') ])

            horse.add_value('birthdate', birthyear)
            horse.add_value('sex', row[3].xpath('.//td[1]/text()').get().strip()[-1])

            sire = ItemLoader(item = HorseItem(), selector=row[3].xpath('./td[1]/a'))

            sire.add_value('sex', 'horse')
            sire.add_xpath('name', '.')
            sire.add_xpath('link', './@href')

            horse.add_value('sire', sire.load_item())

            dam = ItemLoader(item = HorseItem(), selector=row[4].xpath('./td[1]/a[1]'))

            dam.add_value('sex', 'mare')
            dam.add_xpath('name', '.')
            dam.add_xpath('link', './@href')

            dam_sire = ItemLoader(item = HorseItem(), selector=row[4].xpath('./td[1]/a[2]'))

            dam_sire.add_value('sex', 'horse')
            dam_sire.add_xpath('name', '.')
            dam_sire.add_xpath('link', './@href')

            dam.add_value('sire', dam_sire.load_item())

            horse.add_value('dam', dam.load_item())

            starter.add_value('horse', horse.load_item())

            starters.append(starter.load_item())

        race.add_value('starters', starters)

        raceday.add_value('races', race.load_item())

        if len(races) == 0:
            yield raceday.load_item()

        else:
            yield SplashRequest(url=RACE_URL.format(races[0].get_output_value('link')),
                                callback=self.parse_race,
                                cb_kwargs=dict(raceday=raceday),
                                meta = {'races': races})
