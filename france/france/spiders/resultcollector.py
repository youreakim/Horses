from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.loader import ItemLoader
from france.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

from scrapy_splash import SplashRequest

from datetime import date, timedelta, datetime
import os

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/france'

BASE_URL = 'https://www.letrot.com'
CALENDAR_URL = BASE_URL + '/fr/courses/calendrier-resultats?publish_up={}&publish_down={}'
RACEDAY_URL = BASE_URL + '/stats/courses/programme/{}'
RACE_URL = BASE_URL + '/stats/fiche-course/{}/resultats/arrivee-definitive'

class ResultCollector(Spider):
    """
    Collects results from 'letrot.com'
    Takes a start_date and an end_date, in the form of '%Y-%m-%d', these default
    to yesterday.
    """
    name = 'resultcollector'
    allowed_domains = ['letrot.com']

    def __init__(self, start_date = '', end_date = '', *args, **kwargs):
        super(ResultCollector, self).__init__(*args, **kwargs)
        yesterday = date.today() - timedelta(days = 1)
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date != '' else yesterday
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d') if end_date != '' else yesterday

    def start_requests(self):
        url = CALENDAR_URL.format(self.start_date.strftime('%d-%m-%Y'), self.end_date.strftime('%d-%m-%Y'))
        yield SplashRequest(url, self.parse_days)

    def parse_days(self, response):
        for current_day in response.xpath('//div[@class="reunionType"]/a'):
            raceday = ItemLoader(item = RacedayItem(), selector=current_day)

            raceday.add_xpath('racetrack', '.')

            raceday.add_xpath('racetrack_code', './@href')
            raceday.add_xpath('date', './@href')
            raceday.add_xpath('link', './@href')
            raceday.add_value('status', 'result')
            raceday.add_value('collection_date', date.today().strftime('%Y-%m-%d'))

            filename = '_'.join([raceday.get_output_value('date').replace('-', '_'),
                                raceday.get_output_value('racetrack_code')]) + '.json'

            if not os.path.exists(os.path.join(JSON_DIRECTORY, 'result', filename)):
                yield SplashRequest(RACEDAY_URL.format(raceday.get_output_value('link')),
                              self.parse_raceday,
                              cb_kwargs = dict(raceday=raceday),
                              args = {'wait': 5})


    def parse_raceday(self, response, raceday):
        races = []

        race_rows = response.xpath('//div[@class="course"]')
        finished_races = response.xpath('//div[@class="top5"]/text()')

        # only collect days that all the races have finished results
        if len(race_rows) == len(finished_races):
            for current_race in race_rows:
                race = ItemLoader(item = RaceItem(), selector=current_race)

                race.add_xpath('link', './a/@href')
                race.add_value('racetype', 'race')
                race.add_xpath('racenumber', './a/@href')

                race.add_xpath('purse', './/span[@class="allocations nowrap"]')

                race.add_xpath('distance', './/span[@class="conditions"]')
                race.add_xpath('monte', './/span[@class="conditions"]')

                race.add_xpath('startmethod', './/span[@class="conditions"]/span')
                race.add_xpath('conditions', './/span[@class="conditions"]/span/text()')

                race.add_xpath('racename', './/span[@class="prix"]')

                races.append({'link': race.get_output_value('link'), 'race': race})

            yield SplashRequest(RACE_URL.format(races[0]['link']),
                                self.parse_race,
                                cb_kwargs=dict(raceday=raceday, races=races),
                                args = {'wait': 5})


    def parse_race(self, response, raceday, races):
        race = races.pop(0)['race']

        for order, row in enumerate(response.xpath('//table[@id="result_table"]//tr')[ 1 : ], 1):
            starter = ItemLoader(item=RaceStarterItem(), selector=row)

            starter.add_value('order', order)

            # a new column was added some time ago to the results
            add_columns = 0 if len(row.xpath('./td')) == 11 else 1

            finish = row.xpath('./td[1]/span[@class="bold"]/text()').extract_first()

            if finish.isnumeric():
                starter.add_value('finish', int(finish))
                starter.add_value('disqualified', False)
                starter.add_value('started', True)

            elif finish[0] == 'D':
                starter.add_value('finish', 0)
                starter.add_value('disqualified', True)
                starter.add_value('disqstring', finish)
                starter.add_value('started', True)

            elif finish == 'NP':
                starter.add_value('started', False)

            starter.add_xpath('startnumber', './td[2]')

            horse = ItemLoader(item = HorseItem(), selector=row.xpath('./td[3]/a'))

            horse.add_xpath('name', '.')
            horse.add_xpath('country', '.')
            horse.add_xpath('link', './@href')

            horse.add_value('sex', row.xpath(f'./td[{5 + add_columns}]/text()').get())
            horse.add_value('birthdate', row.xpath(f'./td[{6 + add_columns}]/text()').get())

            starter.add_value('horse', horse.load_item())

            starter.add_xpath('driver', f'./td[{7 + add_columns}]/a')
            starter.add_xpath('distance', f'./td[{8 + add_columns}]')
            starter.add_xpath('racetime', f'./td[{10 + add_columns}]/text()')
            starter.add_xpath('purse', f'./td[{11 + add_columns}]')

            race.add_value('starters', starter.load_item())

        raceday.add_value('races', race.load_item())

        if len(races) == 0:
            yield raceday.load_item()

        else:
            yield SplashRequest(RACE_URL.format(races[0]['link']),
                                self.parse_race,
                                cb_kwargs=dict(raceday=raceday, races=races),
                                args = {'wait': 5})
