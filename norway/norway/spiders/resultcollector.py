from scrapy.http import JsonRequest
from scrapy.spiders import Spider
from scrapy.loader import ItemLoader

import json
import os
from datetime import date, datetime, timedelta

from norway.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/norway'
BASE_URL = 'https://www.rikstoto.no/Resultater/'


class ResultCollector(Spider):
    """
    Collects results from the API at 'rikstoto.no'
    A start_date and/or an end_date can be chosen, these defaults to yesterday.

    Results older than six years from the current date needs to be collected
    from 'travsport.no', will do this at another time.
    """
    name = 'resultcollector'
    allowed_domains = ['rikstoto.no', 'travsport.no']

    def __init__(self, start_date = '', end_date = '', *args, **kwargs):
        super(ResultCollector, self).__init__(*args, **kwargs)
        yesterday = date.today() - timedelta(days = 1)
        self.start_date = yesterday if start_date == '' else datetime.strptime(start_date, '%Y-%m-%d').date()
        self.end_date = yesterday if end_date == '' else datetime.strptime(end_date, '%Y-%m-%d').date()


    def start_requests(self):
        """
        Get a list of available racedays between start_date and end_date,
        one week at a time.
        """
        current_date = self.start_date

        while current_date <= self.end_date:
            difference = self.end_date - current_date

            if difference.days < 7:
                url = f'https://www.rikstoto.no/api/results/racedays/{current_date.strftime("%Y-%m-%d")}/{self.end_date.strftime("%Y-%m-%d")}/list'

            else:
                url = f'https://www.rikstoto.no/api/results/racedays/{current_date.strftime("%Y-%m-%d")}/{(current_date + timedelta(days=6)).strftime("%Y-%m-%d")}/list'

            yield JsonRequest(
                url=url,
                callback=self.parse
            )

            current_date += timedelta(days=7)


    def parse(self, response):
        """
        Parse the list of available racedays, remove all that are foreign,
        multitrack, not finished or gallop racedays. Also checks if the day has
        not already been collected.
        """
        response_json = json.loads(response.body)

        for day_json in response_json['result']:
            for raceday_json in day_json['raceDays']:
                if (raceday_json['sportType'] == 'T' and
                    raceday_json.get('isDomestic') and
                    raceday_json['progressStatus'] == 'Finished' and
                    not raceday_json.get('isMultiTrack', False)):

                    raceday = ItemLoader(item=RacedayItem())

                    raceday.add_value('status', 'result')
                    raceday.add_value('racetrack', raceday_json['raceDayName'])
                    raceday.add_value('racetrack_code', raceday_json['trackCode'])
                    raceday.add_value('link', raceday_json['raceDay'])
                    raceday.add_value('date', raceday_json['startTime'].split('T')[0])

                    outfile = '_'.join([
                        raceday.get_output_value('date').replace('-', '_'),
                        raceday.get_output_value('racetrack').lower() + '.json'
                    ])

                    if not os.path.exists(os.path.join(JSON_DIRECTORY, 'result', outfile)):
                        yield JsonRequest(
                            url=f'https://www.rikstoto.no/api/racedays/{raceday.get_output_value("link")}/scratched',
                            callback=self.parse_scratched,
                            cb_kwargs=dict(raceday=raceday)
                        )

    def parse_scratched(self, response, raceday):
        """
        Get a listing of scratched horsese for the current raceday.
        """
        response_json = json.loads(response.body)

        yield JsonRequest(
            url=f'https://www.rikstoto.no/api/results/racedays/{raceday.get_output_value("link")}/raceresults',
            callback=self.parse_odds,
            cb_kwargs=dict(raceday=raceday, scratched=response_json['result'])
        )


    def parse_odds(self, response, raceday, scratched):
        """
        Get a listing of win and show odds for the current raceday.
        """
        response_json = json.loads(response.body)

        odds = {'win': response_json['result']['finalOdds']['winOdds'],
                'place': response_json['result']['finalOdds']['placeOdds']}

        yield JsonRequest(
            url=f'https://www.rikstoto.no/api/racedays/{raceday.get_output_value("link")}/raceInfo',
            callback=self.parse_races,
            cb_kwargs=dict(raceday=raceday, scratched=scratched, odds=odds)
        )


    def parse_races(self, response, raceday, scratched, odds):
        """
        Get the list of races for the current raceday.
        """
        response_json = json.loads(response.body)

        races = []

        for race_json in response_json['result']:
            race = ItemLoader(item=RaceItem())

            race.add_value('racenumber', race_json['raceNumber'])
            race.add_value('race_name', race_json['raceName'])
            race.add_value('distance', race_json['distance'])
            race.add_value('startmethod', race_json['startMethod'])
            race.add_value('conditions', race_json['propositions'])
            race.add_value('purse', race_json['propositions'])
            race.add_value('monte', race_json['isMonte'])

            races.append(race)

        yield JsonRequest(
            url=f'https://www.rikstoto.no/api/results/raceDays/{raceday.get_output_value("link")}/{races[0].get_output_value("racenumber")}/completeresults',
            callback=self.parse_raceresult,
            cb_kwargs=dict(
                raceday=raceday,
                scratched=scratched,
                odds=odds,
                races=races
            )
        )


    def parse_raceresult(self, response, raceday, scratched, odds, races):
        """
        Loop through all the races and get the full result for each race.
        """
        race = races.pop(0)

        race_scratched = scratched.get(str(race.get_output_value('racenumber')), [])
        win_odds = odds['win'].get(str(race.get_output_value('racenumber')), {})
        place_odds = odds['place'].get(str(race.get_output_value('racenumber')), {})

        response_json = json.loads(response.body)

        for starter_json in response_json['result']['results']:
            starter = ItemLoader(item=RaceStarterItem())

            starter.add_value('finish', starter_json['place'])
            starter.add_value('order', starter_json['order'])
            starter.add_value('startnumber', starter_json['startNumber'])
            starter.add_value('postposition', starter_json['postPosition'])
            starter.add_value('distance', starter_json['distance'])
            starter.add_value('driver', starter_json['driverName'])
            starter.add_value('purse', starter_json['prize']/100 if starter_json['prize'] else 0)
            starter.add_value('racetime', starter_json['kmTime'])
            starter.add_value('disqualified', starter_json['kmTime'])
            starter.add_value('disqstring', starter_json['kmTime'])
            starter.add_value('gallop', starter_json['kmTime'])
            starter.add_value('dnf', starter_json['kmTime'])
            starter.add_value('ev_odds', starter_json['odds'])
            starter.add_value('started', starter.get_output_value('startnumber') not in race_scratched)


            if str(starter.get_output_value('startnumber')) in win_odds:
                starter.add_value('odds',
                    win_odds[str(starter.get_output_value('startnumber'))]['odds'])

            if str(starter.get_output_value('startnumber')) in place_odds:
                starter.add_value('show_odds',
                    place_odds[str(starter.get_output_value('startnumber'))]['odds'])

            horse = ItemLoader(item=HorseItem())

            horse.add_value('name', starter_json['horseName'])
            horse.add_value('country', starter_json['horseName'])
            horse.add_value('registration', starter_json['horseRegistrationNumber'])
            horse.add_value('link', starter_json['horseRegistrationNumber'])
            horse.add_value('ueln', starter_json['horseRegistrationNumber'])

            starter.add_value('horse', horse.load_item())

            race.add_value('starters', starter.load_item())

        raceday.add_value('races', race.load_item())

        if len(races) == 0:
            yield raceday.load_item()

        else:
            yield JsonRequest(
                url=f'https://www.rikstoto.no/api/results/raceDays/{raceday.get_output_value("link")}/{races[0].get_output_value("racenumber")}/completeresults',
                callback=self.parse_raceresult,
                cb_kwargs=dict(
                    raceday=raceday,
                    scratched=scratched,
                    odds=odds,
                    races=races
                )
            )
