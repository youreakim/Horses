from scrapy.spiders import Spider
from scrapy.http import JsonRequest
from scrapy.loader import ItemLoader
from sweden.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

from datetime import date, timedelta
import json
import os

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/sweden'

BASE_URL = 'https://api.travsport.se/webapi/raceinfo'
CALENDAR_URL = BASE_URL + '/organisation/TROT/sourceofdata/BOTH?fromracedate={}&tosubmissiondate={}&toracedate={}'
RACEDAY_URL = BASE_URL + '/startlists/organisation/TROT/sourceofdata/SPORT/racedayid/{}'


class StartlistCollector(Spider):
    """
    Collects startlists from https://sportapp.travsport.se for the coming week.
    """
    name = 'startlistcollector'
    allowed_domains = ['api.travsport.se']

    def __init__(self, *args, **kwargs):
        super(StartlistCollector, self).__init__(*args, **kwargs)
        self.start_date = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        self.end_date = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')


    def start_requests(self):
        yield JsonRequest(
            url=CALENDAR_URL.format(self.start_date, self.end_date, self.end_date),
            callback=self.parse)


    def parse(self, response):
        response_json = json.loads(response.body)

        for raceday_json in response_json:
            filename = '_'.join([raceday_json['raceDayDate'].replace('-', '_'),
                                raceday_json['trackName'].lower()]) + '.json'

            outfile = os.path.join(JSON_DIRECTORY, 'startlist', filename)

            if raceday_json['hasNewStartList'] and not os.path.exists(outfile):
                raceday = ItemLoader(item=RacedayItem())

                raceday.add_value('date', raceday_json['raceDayDate'])
                raceday.add_value('racetrack', raceday_json['trackName'])
                raceday.add_value('link', raceday_json['raceDayId'])
                raceday.add_value('status', 'startlist')

                yield JsonRequest(
                    url=RACEDAY_URL.format(raceday_json['raceDayId']),
                    callback=self.parse_raceday,
                    cb_kwargs=dict(raceday=raceday))


    def parse_raceday(self, response, raceday):
        response_json = json.loads(response.body)

        for race_json in response_json['raceList']:
            race = ItemLoader(item=RaceItem())

            race.add_value('link', race_json['raceId'])
            race.add_value('racenumber', race_json['raceNumber'])
            race.add_value('distance', race_json['distance'])
            race.add_value('racetype', race_json['raceType']['code'])
            [race.add_value('conditions', x['text']) for x in race_json['propTexts']]
            race.add_value('startmethod', [x['text'] for x in race_json['propTexts'] if x['typ'] == 'T'][0])
            race.add_value('monte', [x['text'] for x in race_json['propTexts'] if x['typ'] == 'T'][0])

            for starter_json in race_json['horses']:
                starter = ItemLoader(item=RaceStarterItem())

                starter.add_value('driver', starter_json['driver']['name'])
                starter.add_value('trainer', starter_json['trainer']['name'])
                starter.add_value('postposition', starter_json['startPosition'])
                starter.add_value('startnumber', starter_json['programNumber'])
                starter.add_value('distance', starter_json['actualDistance'])
                starter.add_value('started', not starter_json['horseWithdrawn'])

                horse = ItemLoader(item=HorseItem())

                horse.add_value('link', starter_json['id'])
                horse.add_value('name', starter_json['name'])
                horse.add_value('country', starter_json['name'])
                horse.add_value('sex', starter_json['horseGender']['code'])
                horse.add_value('breeder', starter_json['breeder'].get('name'))

                starter.add_value('horse', horse.load_item())

                race.add_value('starters', starter.load_item())

            raceday.add_value('races', race.load_item())

        yield raceday.load_item()
