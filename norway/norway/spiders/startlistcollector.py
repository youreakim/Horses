from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from scrapy_splash import SplashRequest

import json
import os
from datetime import date, timedelta
from base64 import b64decode

from norway.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/norway'

class StartlistCollector(Spider):
    """
    Collects entries from 'rikstoto.no'
    Limited to the closest week, checks if there is a json file already saved for
    the raceday, if not it is collected
    """
    name = 'startlistcollector'
    allowed_domains = ['rikstoto.no']

    def __init__(self, *args, **kwargs):
        super(StartlistCollector, self).__init__(*args, **kwargs)
        self.lua_source = """
                          function main(splash, args)
                            splash.response_body_enabled = true
                            assert(splash:go(args.url))
                            assert(splash:wait(5))
                            return splash:har()
                          end
                          """

    def start_requests(self):
        yield SplashRequest('https://www.rikstoto.no/Spill',
                            self.parse,
                            endpoint = 'execute',
                            args = {'wait': 5,
                                    'lua_source': self.lua_source})

    def parse(self, response):
        json_response = response.data

        for entry in json_response['log']['entries']:
            if entry['response']['url'] == 'https://www.rikstoto.no/api/racedays' :
                racedays_json = json.loads(b64decode(entry['response']['content']['text']))

                for raceday_json in racedays_json['result']:
                    raceday_date = raceday_json['startTime'].split('T')[0]

                    # have this raceday been collected
                    outfile = '_'.join([
                        raceday_date.replace('-', '_'),
                        raceday_json['raceDayName'].lower() + '.json'
                    ])

                    if (raceday_json['countryIsoCode'] == 'NO' and
                            not os.path.exists(os.path.join(JSON_DIRECTORY, 'startlist', outfile))):

                        raceday = ItemLoader(item = RacedayItem())

                        raceday.add_value('date', raceday_date)
                        raceday.add_value('racetrack', raceday_json['raceDayName'])
                        raceday.add_value('racetrack_code', raceday_json['trackCode'])
                        raceday.add_value('status', 'startlist')

                        url = 'https://www.rikstoto.no/Spill/{}/VP?race=2&betMethod=Vanlig'.format(raceday_json['raceDayKey'])

                        yield SplashRequest(url,
                                             self.parse_raceday,
                                             endpoint = 'execute',
                                             args = {'wait': 5,
                                                     'lua_source': self.lua_source},
                                             cb_kwargs = dict(raceday=raceday))


    def parse_raceday(self, response, raceday):
        for entry in response.data['log']['entries']:
            # we only need these two files
            if entry['response']['url'].endswith('/scratched'):
                scratched_json = json.loads(b64decode(entry['response']['content']['text']))
            elif entry['response']['url'].endswith('/trot'):
                raceday_json = json.loads(b64decode(entry['response']['content']['text']))

        races = []

        for race_json in raceday_json['result']:
            scratched = []

            if str(race_json['raceNumber']) in scratched_json:
                scratched = scratched_json['result'][str(race_json['raceNumber'])]

            race = ItemLoader(item = RaceItem())

            purse = race_json['propositions'][ race_json['propositions'].rfind(':') + 1 : ]

            if purse.endswith('kr.'):
                purse = purse[ : purse.rfind(' ') ]
            elif ')' in purse:
                purse = purse[ : purse.rfind('(') ]

            purse = purse.replace('(', '').replace(')', '').replace('.', '')
            race.add_value('purse', sum([int(x) for x in purse.split('-')]))

            race.add_value('racenumber', race_json['raceNumber'])
            race.add_value('race_name', race_json['raceName'])
            race.add_value('conditions', race_json['propositions'])
            race.add_value('startmethod', race_json['startMethod'])
            race.add_value('monte', race_json['isMonte'])
            race.add_value('distance', race_json['distance'])
            race.add_value('racetype', 'race')
            race.add_value('status', 'startlist')

            starters = []

            for starter_json in race_json['starts']:
                starter = ItemLoader(item = RaceStarterItem())

                if ')' in starter_json['trainer']:
                    starter_json['trainer'] = starter_json['trainer'][ : starter_json['trainer'].rfind(' (') ]

                starter.add_value('startnumber', starter_json['startNumber'])
                starter.add_value('driver', starter_json['driver'])

                starter.add_value('distance',
                    race_json['distance'] + starter_json.get('extraDistance', 0))

                starter.add_value('postposition', starter_json['postPosition'])
                starter.add_value('trainer', starter_json['trainer'])

                starter.add_value('started', starter_json['startNumber'] not in scratched)

                horse = ItemLoader(item = HorseItem())

                horse.add_value('name', starter_json['horseName'])
                horse.add_value('sex', starter_json['sex'])
                horse.add_value('registration', starter_json['horseRegistrationNumber'])
                horse.add_value('country', starter_json['horseName'])

                starter.add_value('horse', horse.load_item())

                starters.append(starter.load_item())

            race.add_value('starters', starters)

            races.append(race.load_item())

        raceday.add_value('races', races)

        yield raceday.load_item()
