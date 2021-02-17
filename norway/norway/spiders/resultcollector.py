from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from scrapy_splash import SplashRequest

import locale
import json
import os
import math
from datetime import date, datetime, timedelta
from base64 import b64decode

from norway.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/norway'
BASE_URL = 'https://www.rikstoto.no/Resultater/'

"""
Each calendar week returns these files
======================================
list
    result contains a list for each of the seven days, each contains a dict, where
    date contains a JavaScript date string (split by 'T'), and raceDays that holds
    the list of racedays, each day is a dict, find countryIsoCode and only select
    those days where this is 'NO' and sportType == 'T', find also raceDay which is
    the link to the raceday 'https://www.rikstoto.no/Resultater/{raceDay}'

Each raceday returns these files
================================
starts (all this information is available in completeresults)
    a dict where 'result' contains a list of starters for each race on that raceday
    {raceNumber, startNumber, horseRegistrationNumber, horseName, driverLicenseNumber,
    driverName, extraDistance}
    horseName may contain a non-ISO country code

scratched
    a dict, result contains a dict, key is the racenumber and the value is a list
    of the startnumbers of the horses scratched in that race

raceresults
    result dict contains finalOdds, in this dict placeOdds and winOdds can be found,
    each of these contains a dict where the key is the racenumber and the value is
    a dict with keys of the startnumber and odds of the horses that placed


Each race contains these two interesting files
==============================================
completeresults
    result contains a dict the information of interest is distance, startMethod,
    isComplete(true), plus a resultdict for each horse:
    {order, startNumber, postPosition, distance, horseName, horseRegistrationNumber,
    driverName, prize, kmTime, odds}
    prize is null for unplaced horse, horseName can contain countryCode and *

raceInfo
    result contains a list of racedicts, each contains:
    {raceNumber, raceName, distance, startMethod, propositions, isMonte}
"""

class ResultCollector(Spider):
    """
    Collects results from 'rikstoto.no'
    A start_date and/or an end_date can be chosen, these defaults to yesterday

    An check to see if the day has already been collected should be added
    I think the cookie consent can get in the way sometimes, so occasionaly it fails
    """
    name = 'resultcollector'
    allowed_domains = ['rikstoto.no', 'travsport.no']

    def __init__(self, start_date = '', end_date = '', *args, **kwargs):
        super(ResultCollector, self).__init__(*args, **kwargs)
        yesterday = date.today() - timedelta(days = 1)
        self.start_date = yesterday if start_date == '' else datetime.strptime(start_date, '%Y-%m-%d').date()
        self.end_date = yesterday if end_date == '' else datetime.strptime(end_date, '%Y-%m-%d').date()

        self.lua_source = """
                          function main(splash, args)
                            splash.response_body_enabled = true
                            splash.private_mode_enabled = false
                            assert(splash:go(args.url))
                            assert(splash:wait(5))
                            local links = splash:select_all('tr.race-table-race-header complete-race-results button.btn--link')
                            local cookie = splash:select('div.cookie-container button.button.ng-star-inserted')
                        	if cookie then
                                cookie:mouse_click()
                            end
                            local linkLength = #links
                            for index = 1, linkLength do
                                links[index]:mouse_click()
                                splash:wait(2)
                                -- click in the top left corner to close the modal
                                -- trying to find the close button failed
                                splash:mouse_click(10, 10)
                                assert(splash:wait(0.5))
                                links = splash:select_all('tr.race-table-race-header complete-race-results button.btn--link')
                            end
                            return splash:har()
                          end
                          """

    def start_requests(self):
        if self.start_date >= date.today() - timedelta(days=6):
            yield SplashRequest(url=BASE_URL,
                                callback=self.parse_calendar,
                                endpoint='execute',
                                args={
                                    'wait': 5,
                                    'timeout': 90,
                                    'lua_source': """
                                                  function main(splash, args)
                                                    splash.response_body_enabled = true
                                                    splash.private_mode_enabled = false
                                                    assert(splash:go(args.url))
                                                    assert(splash:wait(5))
                                                    return splash:har()
                                                  end
                                                  """
                                })

        else:
            # if the start_date is not within the last week
            # the lua script will:
            # click on 'button.datepicker__open-btn'
            # click on 'button#prevMonthBtn' while 'span.month-control__date'
            #   does not equal end_date.strftime('%B %Y').lower() for the
            #   norwegian locale 'locale.setlocale(locale.LC_TIME, "nb_NO.utf8")'
            # click on 'span.calendar__dates__days__day' for the day of end_date
            # if there is a greater difference than a week click on
            #   'div.pagination icon' the number of times needed to get to start_date
            #   wait between each click
            # return splash:har()
            locale.setlocale(locale.LC_TIME, "nb_NO.utf8")

            # uses an empty string if the end_date is in the current month
            end_string = ''

            if date.today().month != self.end_date.month:
                end_string = self.end_date.strftime('%B %Y')

            # To click on the right element in the calendar add the weekday
            # value of first of the month
            end_day = self.end_date.day + self.end_date.replace(day=1).weekday()

            # how many weeks needs to be collected
            # this will probably get one week extra, but we can live with that
            difference = self.end_date - self.start_date

            if difference.days < 7:
                weeks = 1
            else:
                weeks = math.ceil(difference.days / 7)

            yield SplashRequest(url = BASE_URL,
                                callback = self.parse_calendar,
                                endpoint='execute',
                                args={
                                    'end_string': end_string,
                                    'end_day': end_day,
                                    'weeks': weeks,
                                    'timeout': 90,
                                    'lua_source': """
                                                    function main(splash, args)
                                                    splash.response_body_enabled = true
                                                    splash.private_mode_enabled = false
                                                    assert(splash:go(args.url))
                                                    assert(splash:wait(5))
                                                    local cookie = splash:select('div.cookie-container button.button.ng-star-inserted')
                                                    if cookie then
                                                        cookie:mouse_click()
                                                    end
                                                    if args.end_string == '' then
                                                        local open = splash:select('button.datepicker__open-btn')
                                                        open:mouse_click()
                                                        assert(splash:wait(0.2))
                                                        local dates = splash:select_all('span.calendar__dates__days__day')
                                                        dates[args.end_day]:mouse_click()
                                                        assert(splash:wait(2))
                                                    else
                                                        local open = splash:select('button.datepicker__open-btn')
                                                        open:mouse_click()
                                                        assert(splash:wait(0.2))
                                                        local calendarHeader = splash:select('span.month-control__date'):text()
                                                        while calendarHeader ~= args.end_string do
                                                            local prev = splash:select('button#prevMonthBtn')
                                                            prev:mouse_click()
                                                            assert(splash:wait(0.2))
                                                            calendarHeader = splash:select('span.month-control__date'):text()
                                                        end
                                                        local dates = splash:select_all('span.calendar__dates__days__day')
                                                        dates[args.end_day]:mouse_click()
                                                        assert(splash:wait(2))
                                                    end
                                                    local counter = 0
                                                    while counter < args.weeks do
                                                        local prevWeek = splash:select('div.pagination icon')
                                                        prevWeek:mouse_click()
                                                        assert(splash:wait(2))
                                                        counter = counter + 1
                                                    end
                                                    return splash:har()
                                                    end
                                                  """
                                })

    def parse_calendar(self, response):
        for entry in response.data['log']['entries']:
            url_split = entry['response']['url'].split('/')

            if url_split[-1].lower() == 'list':
                # contains all the racedays for the current week
                week_json = json.loads(b64decode(entry['response']['content']['text']))

                for day_json in week_json['result']:
                    current_date = day_json['date'].split('T')[0]
                    current_date = datetime.strptime(current_date, '%Y-%m-%d').date()

                    if self.start_date <= current_date <= self.end_date:
                        # we have arrived at a date we are looking for
                        for raceday_json in day_json['raceDays']:
                            if raceday_json['sportType'] == 'T' and raceday_json['countryIsoCode'] == 'NO':
                                # we are only interested in norwegian harness racedays
                                raceday = ItemLoader(item=RacedayItem())

                                raceday.add_value('date', current_date.strftime('%Y-%m-%d'))
                                raceday.add_value('racetrack', raceday_json['raceDayName'])
                                raceday.add_value('link', raceday_json['raceDay'])
                                raceday.add_value('status', 'result')

                                if raceday_json['progressStatus'] == 'Abandoned':
                                    # the raceday has been cancelled
                                    # we don't need to go any further
                                    raceday.add_value('cancelled', True)
                                    yield raceday.load_item()

                                else:
                                    yield SplashRequest(
                                        url=BASE_URL + raceday_json['raceDay'],
                                        callback=self.parse_raceday,
                                        cb_kwargs=dict(
                                            raceday=raceday,
                                            no_races=len(raceday_json['races'])
                                        ),
                                        endpoint='execute',
                                        args={
                                            'wait': 5,
                                            'timeout': 90,
                                            'lua_source': self.lua_source
                                        }
                                    )

    def parse_raceday(self, response, raceday, no_races):
        all_starters = {x: [] for x in range(1, no_races + 1)}
        scratched = {x: [] for x in range(1, no_races + 1)}
        odds = {x: {'win': {}, 'show': {}} for x in range(1, no_races + 1)}
        races = {x: None for x in range(1, no_races + 1)}

        for entry in response.data['log']['entries']:
            url_split = entry['response']['url'].split('/')
            file = url_split[-1].lower()

            if file == 'scratched':
                scratched_json = json.loads(b64decode(entry['response']['content']['text']))
                scratched.update(scratched_json['result'])

            elif file == 'raceresults':
                odds_json = json.loads(b64decode(entry['response']['content']['text']))

                for racenumber, places in odds_json['result']['finalOdds']['placeOdds'].items():
                    for startnumber, odds_dict in places.items():
                        odds[int(racenumber)]['show'][int(startnumber)] = odds_dict['odds']

                for racenumber, places in odds_json['result']['finalOdds']['winOdds'].items():
                    for startnumber, odds_dict in places.items():
                        odds[int(racenumber)]['win'][int(startnumber)] = odds_dict['odds']

            elif file == 'completeresults':
                starters = []
                starters_json = json.loads(b64decode(entry['response']['content']['text']))

                for starter_json in starters_json['result']['results']:
                    starter = ItemLoader(item=RaceStarterItem())

                    horse = ItemLoader(item=HorseItem())

                    horse.add_value('name', starter_json['horseName'])
                    horse.add_value('country', starter_json['horseName'])
                    horse.add_value('registration', starter_json['horseRegistrationNumber'])
                    horse.add_value('link', starter_json['horseRegistrationNumber'])

                    if len(starter_json['horseRegistrationNumber']) == 15:
                        horse.add_value('ueln', starter_json['horseRegistrationNumber'])

                    starter.add_value('horse', horse.load_item())
                    starter.add_value('startnumber', starter_json['startNumber'])
                    starter.add_value('finish', starter_json['place'])
                    starter.add_value('order', starter_json['order'])
                    starter.add_value('postposition', starter_json['postPosition'])
                    starter.add_value('distance', starter_json['distance'])
                    starter.add_value('driver', starter_json['driverName'])
                    starter.add_value('purse', starter_json['prize'] / 100 if starter_json['prize'] else 0)
                    starter.add_value('started', True)
                    starter.add_value('ev_odds', starter_json['odds'])

                    # kmTime contains a lot of information
                    # the racetime of the horse and
                    # if the horse has made a break, is disqualified, has not finished the race,...
                    # need to check if this gets it right
                    if starter_json['kmTime']:
                        time_string = starter_json['kmTime']

                        if ',' in time_string:
                            starter.add_value('racetime', float(time_string[:4].replace(',', '.')) + 60)
                            time_string = time_string[ 4 : ].strip()

                        else:
                            if 'br' in time_string:
                                starter.add_value('dnf', True)
                                time_string = time_string.replace('br', '').strip()

                            if time_string.startswith('d'):
                                starter.add_value('disqualified', True)
                                time_string = time_string[ 1 : ].strip()

                        if 'g' in time_string:
                            starter.add_value('gallop', True)
                            time_string = time_string.replace('g', '').strip()

                        time_string = time_string.replace('a', '').strip()

                        if time_string != '' and not starter.get_output_value('racetime'):
                            starter.add_value('disqstring', time_string)

                    starters.append(starter)

                all_starters[int(url_split[-2])] = starters

            elif file == 'raceinfo':
                races_json = json.loads(b64decode(entry['response']['content']['text']))

                for race_json in races_json['result']:
                    race = ItemLoader(item=RaceItem())

                    race.add_value('conditions', race_json['propositions'])
                    race.add_value('race_name', race_json['raceName'])
                    race.add_value('distance', race_json['distance'])
                    race.add_value('startmethod', race_json['startMethod'])
                    race.add_value('monte', race_json['isMonte'])
                    race.add_value('racenumber', race_json['raceNumber'])

                    races[race_json['raceNumber']] = race

            # elif file == 'starts':
            #     pass

        for x in range(1, no_races + 1):
            race = races[x]

            for starter in all_starters[x]:
                if starter.get_output_value('startnumber') in scratched[x]:
                    starter.replace_value('started', False)

                if starter.get_output_value('startnumber') in odds[x]['win']:
                    starter.add_value('odds', odds[x]['win'][starter.get_output_value('startnumber')])

                if starter.get_output_value('startnumber') in odds[x]['show']:
                    starter.add_value('show_odds', odds[x]['show'][starter.get_output_value('startnumber')])

                race.add_value('starters', starter.load_item())

            raceday.add_value('races', race.load_item())

        yield raceday.load_item()
