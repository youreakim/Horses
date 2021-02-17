from scrapy.spiders import Spider
from scrapy.http import JsonRequest
from scrapy.loader import ItemLoader
from belgium.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

from datetime import date, timedelta, datetime
import json


JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/belgium'

BASE_URL = 'https://www.trotting.be/API/Home/RaceCalendar'
CALENDAR_URL = BASE_URL + '?startDate={}&endDate={}&showAllDepartments=false'
DAY_URL = BASE_URL + '?activityDay={}'
RACEDAY_URL = BASE_URL + '?trackId={}&activityDay={}&finishedList=true'
RACE_URL = 'https://www.trotting.be/API/Events/RaceResults/?eventId=&raceId={}'


class ResultCollector(Spider):
    """
    Collects results from 'https://www.trotting.be', uses their API.
    Takes a start_date and an end_date, if none is provided these default to
    yesterday.
    """
    name = 'resultcollector'
    allowed_domains = ['trotting.be']


    def __init__(self, start_date='', end_date='', *args, **kwargs):
        super(ResultCollector, self).__init__(*args, **kwargs)
        yesterday = date.today() - timedelta(days=1)
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date != '' else yesterday
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date != '' else yesterday


    def start_requests(self):
        monday = self.end_date - timedelta(days=self.end_date.weekday())
        sunday = self.end_date + timedelta(days=7 - self.end_date.weekday())

        while sunday >= self.start_date:
            yield JsonRequest(
                url=CALENDAR_URL.format(monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')),
                callback=self.parse_calendar
            )

            monday -= timedelta(days=7)
            sunday -= timedelta(days=7)


    def parse_calendar(self, response):
        response_json = json.loads(response.body)

        for day_json in response_json['DepartureDays']:
            current_date = day_json['DepartureDate'].split('T')[0]
            current_date = datetime.strptime(current_date, '%Y-%m-%d').date()

            if self.start_date <= current_date <= self.end_date:
                yield JsonRequest(
                    url=DAY_URL.format(current_date.strftime('%d-%m-%Y')),
                    callback=self.parse_day
                )


    def parse_day(self, response):
        response_json = json.loads(response.body)

        for raceday_json in response_json['Items']:
            raceday = ItemLoader(item=RacedayItem())

            raceday.add_value('racetrack', raceday_json['TrackName'])
            raceday.add_value('racetrack_code', raceday_json['Track_id'])
            raceday.add_value('date', raceday_json['SelectedDate'].split('T')[0])
            raceday.add_value('status', 'result')

            yield JsonRequest(
                url=RACEDAY_URL.format(raceday_json['Track_id'], raceday_json['FormatedSelectedDate']),
                callback=self.parse_raceday,
                cb_kwargs=dict(raceday=raceday)
            )


    def parse_raceday(self, response, raceday):
        response_json = json.loads(response.body)

        races = []

        for race_json in response_json:
            race = ItemLoader(item=RaceItem())

            race.add_value('link', race_json['RaceId'])
            race.add_value('race_name', race_json['Name'])
            race.add_value('racenumber', race_json['RaceNumber'])
            race.add_value('distance', race_json['Distance'])
            race.add_value('monte', race_json['DisciplineText'])
            race.add_value('startmethod', race_json['StartTypeText'])
            race.add_value('racetype', race_json['RaceCategory']['Name'])
            race.add_value('purse', race_json['WinsumPrice'])
            race.add_value('conditions', race_json['RaceDescription'])

            races.append(race)

        yield JsonRequest(
            url=RACE_URL.format(races[0].get_output_value('link')),
            callback=self.parse_race,
            cb_kwargs=dict(raceday=raceday),
            meta={'races': races}
        )


    def parse_race(self, response, raceday):
        response_json = json.loads(response.body)

        race = response.meta['races'].pop(0)
        races = response.meta['races']

        for order, starter_json in enumerate(response_json['Participations'], 1):
            starter = ItemLoader(item=RaceStarterItem())

            starter.add_value('order', order)
            starter.add_value('distance', starter_json['Distance'])
            starter.add_value('startnumber', starter_json['StartNumber'])
            starter.add_value('driver', starter_json['Driver']['Name'])
            starter.add_value('trainer', starter_json['Trainer']['Name'])
            starter.add_value('purse', starter_json['Version']['TotalWinsum'])
            starter.add_value('racetime', starter_json['Version']['FormattedResultTime1000TimeTxt'])
            starter.add_value('started', starter_json['Version']['PlaceText'])
            starter.add_value('disqualified', starter_json['Version']['PlaceText'])

            if starter.get_output_value('started') and not starter.get_output_value('disqualified'):
                starter.add_value('finish', starter_json['Version']['Place'])

            horse = ItemLoader(item=HorseItem())

            horse.add_value('name', starter_json['Horse']['Name'])
            horse.add_value('link', str(starter_json['Horse']['HorseId']))
            horse.add_value('registration', starter_json['Horse']['OldHorseId'])
            horse.add_value('sex', starter_json['Horse']['GenderText'])
            horse.add_value('birthdate', starter_json['Horse']['DateOfBirth'])

            starter.add_value('horse', horse.load_item())

            race.add_value('starters', starter.load_item())

        raceday.add_value('races', race.load_item())

        if len(races) == 0:
            yield raceday.load_item()

        else:
            yield JsonRequest(
                url=RACE_URL.format(races[0].get_output_value('link')),
                callback=self.parse_race,
                cb_kwargs=dict(raceday=raceday),
                meta={'races': races}
            )
