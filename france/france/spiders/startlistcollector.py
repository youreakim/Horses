from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from france.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

from scrapy_splash import SplashRequest

from datetime import date, timedelta, datetime
import os

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/france'

BASE_URL = 'https://www.letrot.com'
CALENDAR_URL = BASE_URL + '/fr/courses/calendrier-resultats?publish_up={}&publish_down={}'
RACEDAY_URL = BASE_URL + '/stats/courses/programme/{}'
RACE_URL = BASE_URL + '/stats/fiche-course/{}/partants/tableau'

class StartlistCollector(Spider):
    """
    Collects results from 'letrot.com'
    Takes a start_date and an end_date, in the form of '%Y-%m-%d', these default
    to tomorrow and six days from today.
    """
    name = 'startlistcollector'
    allowed_domains = ['letrot.com']


    def __init__(self, *args, **kwargs):
        super(StartlistCollector, self).__init__(*args, **kwargs)
        self.start_date = date.today() + timedelta(days = 1)
        self.end_date = date.today() + timedelta(days = 6)


    def start_requests(self):
        url = CALENDAR_URL.format(self.start_date.strftime('%d-%m-%Y'), self.end_date.strftime('%d-%m-%Y'))
        yield SplashRequest(url, self.parse_day)


    def parse_day(self, response):
        for current_day in response.xpath('//div[@class="reunionType"]/a'):
            raceday = ItemLoader(item=RacedayItem(), selector=current_day)

            raceday.add_xpath('racetrack', '.')

            raceday.add_xpath('racetrack_code', './@href')
            raceday.add_xpath('date', './@href')
            raceday.add_xpath('link', './@href')
            raceday.add_value('status', 'startlist')
            raceday.add_value('collection_date', date.today().strftime('%Y-%m-%d'))

            filename = '_'.join([
                raceday.get_output_value('date').replace('-', '_'),
                raceday.get_output_value('racetrack_code')]) + '.json'

            if not os.path.exists(os.path.join(JSON_DIRECTORY, 'startlist', filename)):
                yield SplashRequest(RACEDAY_URL.format(raceday.get_output_value('link')),
                                    self.parse_raceday,
                                    cb_kwargs=dict(raceday=raceday),
                                    args = {'wait': 5})


    def parse_raceday(self, response, raceday):
        races = []

        race_rows = response.xpath('//div[@class="course"]')
        start_times = response.xpath('//div[@class="heure"]')

        # if the startlist is ready it has a start time,
        # only collect if all races have start times
        if len(race_rows) == len(start_times) and len(race_rows) != 0:
            for current_race in race_rows:
                race = ItemLoader(item=RaceItem(), selector=current_race)

                race.add_xpath('link', './a/@href')
                race.add_value('racetype', 'race')
                race.add_xpath('racenumber', './a/@href')
                race.add_xpath('purse', './/span[@class="allocations nowrap"]')
                race.add_xpath('distance', './/span[@class="conditions"]')
                race.add_xpath('monte', './/span[@class="conditions"]')
                race.add_xpath('startmethod', './/span[@class="conditions"]/span')

                # races at Vincennes has an extra span to indicate if they use
                # the small or large track, don't want this
                race.add_xpath('conditions', './/span[@class="conditions"]/span[last()]/text()')

                race.add_xpath('racename', './/span[@class="prix"]')

                races.append(race)

            yield SplashRequest(RACE_URL.format(races[0].get_output_value('link')),
                                self.parse_race,
                                args = {'wait': 5},
                                cb_kwargs=dict(races=races, raceday=raceday))


    def parse_race(self, response, raceday, races):
        race = races.pop(0)

        for row in response.xpath('//table[@id="result_table"]//tr')[ 1 : ]:
            starter = ItemLoader(item=RaceStarterItem(), selector=row)

            starter.add_xpath('startnumber', './td[1]/span[1]')
            starter.add_xpath('started', './td[1]/span[@class="bold"]')

            horse = ItemLoader(item = HorseItem(), selector=row.xpath('./td[2]/a'))

            horse.add_xpath('name', '.')
            horse.add_xpath('country', '.')
            horse.add_xpath('link', './@href')

            horse.add_value('sex', row.xpath('./td[5]/text()').get())
            horse.add_value('birthdate', row.xpath('./td[6]/text()').get())

            starter.add_value('horse', horse.load_item())

            starter.add_xpath('distance', './td[7]')
            starter.add_xpath('driver', './td[8]/a')

            # for monte races there is weight column for the rider
            starter.add_xpath('trainer', f'./td[{10 if race.get_output_value("monte") else 9}]/a')

            race.add_value('starters', starter.load_item())

        raceday.add_value('races', race.load_item())

        if len(races) == 0:
            yield raceday.load_item()

        else:
            yield SplashRequest(RACE_URL.format(races[0].get_output_value('link')),
                                self.parse_race,
                                args = {'wait': 5},
                                cb_kwargs=dict(races=races, raceday=raceday))
