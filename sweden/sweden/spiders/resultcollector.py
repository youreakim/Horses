from scrapy.spiders import Spider
from scrapy.http import JsonRequest
from scrapy.loader import ItemLoader
from sweden.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

from datetime import date, timedelta, datetime
import json
import os


JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/sweden'

BASE_URL_ATG = 'https://www.atg.se/services/racinginfo/v1/api/'
CALENDAR_URL_ATG = BASE_URL_ATG + 'calendar/day/{}'
RESULT_URL_ATG = BASE_URL_ATG + 'games/raket_{}_{}_1'

BASE_URL_ST = 'https://api.travsport.se/webapi/raceinfo/'
CALENDAR_URL_ST = BASE_URL_ST + 'organisation/TROT/sourceofdata/SPORT?fromracedate={}&tosubmissiondate={}&toracedate={}'
RESULT_URL_ST = BASE_URL_ST + 'results/organisation/TROT/sourceofdata/SPORT/racedayid/{}'


class ResultCollector(Spider):
    """
    Collects results from https://www.atg.se (ATG) and https://sportapp.travsport.se (ST).
    Takes a start_date and end_date, in the form 'YYYY-mm-dd', these default to yesterday.
    Starts at ATGs site and collects results for the available racedays, since
    ATG does not show qualifiers and premium races, this information is collected
    from ST.
    """
    name = 'resultcollector'
    allowed_domains = ['atg.se', 'travsport.se']

    def __init__(self, start_date = '', end_date = '', *args, **kwargs):
        super(ResultCollector, self).__init__(*args, **kwargs)
        yesterday = date.today() - timedelta(days = 1)
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date != '' else yesterday
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date != '' else yesterday


    def start_requests(self):
        current_date = self.start_date
        urls = []
        while current_date <= self.end_date:
            urls.append(CALENDAR_URL_ATG.format(current_date.strftime('%Y-%m-%d')))
            current_date += timedelta(days = 1)

        yield JsonRequest(url=urls.pop(0),
                          callback=self.parse_day_atg,
                          meta={'urls': urls, 'racedays': []})


    def parse_day_atg(self, response):
        day_json = json.loads(response.body)

        current_date = day_json['date']

        racedays = response.meta['racedays']

        for raceday_json in day_json['tracks']:
            filename = '_'.join([current_date.replace('-', '_'),
                                 raceday_json['name'].lower() + '.json'])

            if (raceday_json['countryCode'] == 'SE'
                    and raceday_json['sport'] == 'trot'
                    and not os.path.exists(os.path.join(JSON_DIRECTORY, 'result', filename))
                    and 'races' in raceday_json):

                raceday = ItemLoader(item = RacedayItem())

                raceday.add_value('status', 'result')
                raceday.add_value('date', current_date)
                raceday.add_value('racetrack', raceday_json['name'])
                raceday.add_value('racetrack_code', raceday_json['id'])

                racedays.append({
                    'url': RESULT_URL_ATG.format(current_date, raceday_json['id']),
                    'raceday': raceday,
                    'races': {}
                })


        if len(response.meta['urls']) != 0:
            yield JsonRequest(url=response.meta['urls'].pop(0),
                              callback=self.parse_day_atg,
                              meta={'urls': response.meta['urls'],
                                    'racedays': racedays})

        elif len(racedays) != 0:
            yield JsonRequest(url=racedays[0]['url'],
                              callback=self.parse_raceday_atg,
                              meta = {'racedays': racedays})


    def parse_raceday_atg(self, response):
        raceday = [x for x in response.meta['racedays'] if x['url'] == response.url][0]

        raceday_json = json.loads(response.body)

        for race_json in raceday_json['races']:
            race = ItemLoader(item = RaceItem())

            race.add_value('racetype', 'race')
            race.add_value('racenumber', race_json['number'])
            race.add_value('distance', race_json['distance'])
            race.add_value('startmethod', race_json['startMethod'])

            if 'name' in race_json:
                race.add_value('racename', race_json['name'])

            race.add_value('conditions', race_json['terms'])

            if not all([('scratched' in x) for x in race_json['starts']]):
                starts = sorted(race_json['starts'], key = lambda starter: starter['result']['finishOrder'])
            else:
                starts = race_json['starts']

            race_purse = 0

            for order, starter_json in enumerate(starts, 1):
                starter         = ItemLoader(item = RaceStarterItem())

                starter.add_value('startnumber', starter_json['number'])
                starter.add_value('postposition', starter_json['postPosition'])
                starter.add_value('order', order)
                starter.add_value('distance', starter_json['distance'])
                starter.add_value('driver', ' '.join([starter_json['driver']['lastName'], starter_json['driver']['firstName']]))

                if 'trainer' in starter_json['horse']:
                    starter.add_value('trainer',
                        ' '.join([starter_json['horse']['trainer']['lastName'], starter_json['horse']['trainer']['firstName']]))

                horse = ItemLoader(item = HorseItem())

                horse.add_value('name', starter_json['horse']['name'])
                horse.add_value('link', starter_json['horse']['id'])
                horse.add_value('country', starter_json['horse'].get('nationality', 'SE'))
                horse.add_value('sex', starter_json['horse']['sex'])

                sire = ItemLoader(item = HorseItem())

                sire.add_value('name', starter_json['horse']['pedigree']['father']['name'])
                sire.add_value('link', starter_json['horse']['pedigree']['father']['id'])
                sire.add_value('sex', 'horse')
                sire.add_value('country', starter_json['horse']['pedigree']['father'].get('nationality', 'SE'))

                dam = ItemLoader(item = HorseItem())

                dam.add_value('name', starter_json['horse']['pedigree']['mother']['name'])
                dam.add_value('link', starter_json['horse']['pedigree']['mother']['id'])
                dam.add_value('sex', 'mare')
                dam.add_value('country', starter_json['horse']['pedigree']['mother'].get('nationality', 'SE'))

                dam_sire = ItemLoader(item = HorseItem())

                dam_sire.add_value('name', starter_json['horse']['pedigree']['grandfather']['name'])
                dam_sire.add_value('link', starter_json['horse']['pedigree']['grandfather']['id'])
                dam_sire.add_value('sex', 'horse')
                dam_sire.add_value('country', starter_json['horse']['pedigree']['grandfather'].get('nationality', 'SE'))

                dam.add_value('sire', dict(dam_sire.load_item()))

                horse.add_value('sire', dict(sire.load_item()))
                horse.add_value('dam', dict(dam.load_item()))

                starter.add_value('horse', dict(horse.load_item()))

                if 'scratched' in starter_json:
                    starter.add_value('started', False)
                    race.add_value('starters', starter.load_item())
                    continue

                starter.add_value('started', True)

                starter.add_value('gallop', starter_json['result'].get('galloped'))
                starter.add_value('dnf', starter_json['result']['kmTime'].get('code', ''))
                starter.add_value('disqualified', starter_json['result'].get('disqualified', False))

                if starter_json['result'].get('disqualified'):
                    starter.add_value('disqstring', starter_json['result']['kmTime']['code'])

                else:
                    starter.add_value('racetime',
                        (starter_json['result']['kmTime'].get('minutes', 0) * 60 +
                         starter_json['result']['kmTime'].get('seconds', 0) +
                         starter_json['result']['kmTime'].get('tenths', 0) / 10))

                starter.add_value('purse', starter_json['result'].get('prizeMoney'))
                race_purse += starter_json['result'].get('prizeMoney', 0)

                if starter_json['result'].get('place') == 1:
                    starter.add_value('odds', starter_json['result']['finalOdds'])

                if starter_json['pools']['plats'].get('odds'):
                    starter.add_value('show_odds', starter_json['pools']['plats']['odds'] / 100)

                starter.add_value('ev_odds', round(starter_json['result']['finalOdds'] * 10))

                race.add_value('starters', starter.load_item())

            race.add_value('purse', race_purse)

            raceday['races'][race.get_output_value('racenumber')] = race

        # if races has been added to all racedays, head over to ST to get
        # ids, qualifiers and premium races
        if all(bool(x['races']) for x in response.meta['racedays']):
            yield JsonRequest(
                url=CALENDAR_URL_ST.format(self.start_date, self.end_date, self.end_date),
                callback=self.parse_calendar_st,
                meta={'racedays': response.meta['racedays']})

        else:
            url = [x['url'] for x in response.meta['racedays'] if not bool(x['races'])][0]
            yield JsonRequest(url=url,
                              callback=self.parse_raceday_atg,
                              meta = {'racedays': response.meta['racedays']})


    def parse_calendar_st(self, response):
        response_json = json.loads(response.body)

        for raceday_json in response_json:
            # find the raceday in response.meta['racedays']
            for raceday_atg in response.meta['racedays']:
                if (raceday_json['raceDayDate'] == raceday_atg['raceday'].get_output_value('date') and
                    raceday_json['trackName'] == raceday_atg['raceday'].get_output_value('racetrack')):

                    raceday = raceday_atg['raceday']

                    raceday.add_value('link', raceday_json['raceDayId'])

                    yield JsonRequest(
                        url=RESULT_URL_ST.format(raceday_json['raceDayId']),
                        callback=self.parse_raceday_st,
                        cb_kwargs=dict(raceday=raceday),
                        meta={'races': raceday_atg['races']})


    def parse_raceday_st(self, response, raceday):
        response_json = json.loads(response.body)

        for race_json in response_json['racesWithReadyResult']:
            if race_json['generalInfo']['raceNumber'] in response.meta['races']:
                race = response.meta['races'][race_json['generalInfo']['raceNumber']]

                race.add_value('link', race_json['raceId'])

            else:
                race = ItemLoader(item=RaceItem())

                race.add_value('link', race_json['raceId'])
                race.add_value('racenumber', race_json['generalInfo']['raceNumber'])
                race.add_value('conditions', [x['text'] for x in race_json['propositionDetailRows']])
                race.add_value('racetype', race.get_output_value('conditions'))
                race.add_value('monte', race.get_output_value('conditions'))
                race.add_value('startmethod', race.get_output_value('conditions'))
                race.add_value('distance', race.get_output_value('conditions'))

                order = 1

                race_purse = 0

                for starter_json in race_json.get('raceResultRows', []):
                    starter = ItemLoader(item=RaceStarterItem())

                    starter.add_value('order', order)
                    starter.add_value('driver', starter_json['driver']['name'])
                    starter.add_value('trainer', starter_json['trainer']['name'])
                    starter.add_value('postposition', starter_json['startPositionAndDistance'])
                    starter.add_value('distance', starter_json['startPositionAndDistance'])
                    starter.add_value('racetime', starter_json['time'])
                    starter.add_value('disqualified', starter_json['time'])
                    starter.add_value('dnf', starter_json['time'])
                    starter.add_value('gallop', starter_json['time'])
                    starter.add_value('purse', starter_json.get('prizeMoney'))
                    starter.add_value('started', True)
                    starter.add_value('startnumber',starter_json['programNumber'])
                    starter.add_value('purse', starter_json.get('prizeMoney'))

                    race_purse += starter_json.get('prizeMoney', 0)

                    if starter.get_output_value('disqualified'):
                        starter.add_value('disqstring', starter_json['time'])

                    if starter_json.get('odds'):
                        starter.add_value('odds', starter_json['odds'])

                    if starter_json.get('oddsPlats'):
                        starter.add_value('show_odds', starter_json['oddsPlats'])

                    if race.get_output_value('racetype') == 'race':
                        starter.add_value('finish', starter_json['placementNumber'])
                    else:
                        starter.add_value('approved', starter_json['placementDisplay'])

                    horse = ItemLoader(item=HorseItem())

                    horse.add_value('name', starter_json['horse']['name'])
                    horse.add_value('country', starter_json['horse']['name'])
                    horse.add_value('link', starter_json['horse']['id'])

                    starter.add_value('horse', horse.load_item())

                    race.add_value('starters', starter.load_item())

                    order += 1

                if race_purse != 0:
                    race.add_value('purse', race_purse)

                for non_starter_json in race_json.get('withdrawnHorses', []):
                    starter = ItemLoader(item=RaceStarterItem())

                    starter.add_value('startnumber', non_starter_json['programNumber'])
                    starter.add_value('started', False)
                    starter.add_value('order', order)

                    horse = ItemLoader(item=HorseItem())

                    horse.add_value('name', non_starter_json['name'])
                    horse.add_value('country', non_starter_json['name'])
                    horse.add_value('link', non_starter_json['id'])

                    starter.add_value('horse', horse.load_item())

                    race.add_value('starters', starter.load_item())

                    order += 1

            raceday.add_value('races', race.load_item())

        yield raceday.load_item()
