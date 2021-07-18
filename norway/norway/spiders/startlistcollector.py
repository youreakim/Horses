from scrapy.http import JsonRequest
from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from scrapy_splash import SplashRequest

import json
import os
from datetime import date, timedelta

from norway.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/norway'
BASE_URL = 'https://www.rikstoto.no/api'


class StartlistCollector(Spider):
    """
    Collects entries from the api at 'rikstoto.no'.
    """
    name = 'startlistcollector'
    allowed_domains = ['rikstoto.no']


    def start_requests(self):
        """
        Get a list of available racedays.
        """
        yield JsonRequest(
            url=f'{BASE_URL}/racedays',
            callback=self.parse
        )


    def parse(self, response):
        """
        Parse the list of available racedays, remove foreign, multitrack or gallop
        racedays. Checks if the raceday is already collected.
        """
        response_json = json.loads(response.body)

        for raceday_json in response_json['result']:
            if raceday_json['sportType'] == 'T' and raceday_json['isDomestic'] and not raceday_json['isMultiTrack']:
                raceday = ItemLoader(item=RacedayItem())

                raceday.add_value('racetrack', raceday_json['raceDayName'])
                raceday.add_value('date', raceday_json['startTime'].split('T')[0])
                raceday.add_value('racetrack_code', raceday_json['trackCode'])
                raceday.add_value('link', raceday_json['raceDayKey'])
                raceday.add_value('status', 'startlist')

                outfile = '_'.join([
                    raceday.get_output_value('date').replace('-', '_'),
                    raceday.get_output_value('racetrack').lower() + '.json'
                ])

                if not os.path.exists(os.path.join(JSON_DIRECTORY, 'startlist', outfile)):
                    yield JsonRequest(
                        url=f'{BASE_URL}/racedays/{raceday.get_output_value("link")}/scratched',
                        callback=self.parse_scratched,
                        cb_kwargs=dict(raceday=raceday)
                    )


    def parse_scratched(self, response, raceday):
        """
        Parse the list of scratched horses for the current raceday.
        """
        response_json = json.loads(response.body)

        yield JsonRequest(
            url=f'{BASE_URL}/game/program/{raceday.get_output_value("link")}/VP/trot',
            callback=self.parse_raceday,
            cb_kwargs=dict(raceday=raceday, scratched=response_json['result'])
        )


    def parse_raceday(self, response, raceday, scratched):
        """
        Parse the list of races and entries for the raceday.
        """
        response_json = json.loads(response.body)

        for race_json in response_json['result']:
            race_scratched = scratched.get(race_json['raceNumber'], [])

            race = ItemLoader(item=RaceItem())

            race.add_value('racetype', 'race')
            race.add_value('racenumber', race_json['raceNumber'])
            race.add_value('race_name', race_json['raceName'])
            race.add_value('distance', race_json['distance'])
            race.add_value('startmethod', race_json['startMethod'])
            race.add_value('conditions', race_json['propositions'])
            race.add_value('purse', race_json['propositions'])
            race.add_value('monte', race_json['isMonte'])

            for starter_json in race_json['starts']:
                starter = ItemLoader(item=RaceStarterItem())

                starter.add_value('startnumber', starter_json['startNumber'])
                starter.add_value('started', starter.get_output_value('startnumber') not in race_scratched)
                starter.add_value('driver', starter_json['driver'])
                starter.add_value('distance', race.get_output_value('distance') + starter_json['extraDistance'])
                starter.add_value('trainer', starter_json['trainer'])
                starter.add_value('postposition', starter_json['postPosition'])

                horse = ItemLoader(item=HorseItem())

                horse.add_value('name', starter_json['horseName'])
                horse.add_value('country', starter_json['horseName'])
                horse.add_value('sex', starter_json['sex'])
                horse.add_value('birthdate', f'{int(raceday.get_output_value("date")[:4]) - starter_json["age"]}-01-01')
                horse.add_value('registration', starter_json['horseRegistrationNumber'])
                horse.add_value('link', starter_json['horseRegistrationNumber'])
                horse.add_value('ueln', starter_json['horseRegistrationNumber'])

                sire = ItemLoader(item=HorseItem())

                sire.add_value('sex', 'horse')
                sire.add_value('name', starter_json['father'])
                sire.add_value('country', starter_json['father'])

                horse.add_value('sire', sire.load_item())

                dam = ItemLoader(item=HorseItem())

                dam.add_value('sex', 'mare')
                dam.add_value('name', starter_json['mother'])
                dam.add_value('country', starter_json['mother'])

                dam_sire = ItemLoader(item=HorseItem())

                dam_sire.add_value('sex', 'horse')
                dam_sire.add_value('name', starter_json['grandfather'])
                dam_sire.add_value('country', starter_json['grandfather'])

                dam.add_value('sire', dam_sire.load_item())

                horse.add_value('dam', dam.load_item())

                starter.add_value('horse', horse.load_item())

                race.add_value('starters', starter.load_item())

            raceday.add_value('races', race.load_item())

        yield raceday.load_item()
