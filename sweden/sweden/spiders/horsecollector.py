# -*- coding: utf-8 -*-
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import Spider, Rule
from scrapy.http import Request, JsonRequest
from scrapy.loader import ItemLoader
from sweden.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

from scrapy_splash import SplashFormRequest, SplashRequest

from datetime import date, timedelta
import json
import pprint
import re
import os

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/sweden'

BASE_URL = 'https://api.travsport.se/webapi/horses/'
BASIC_INFO_URL = '{}basicinformation/organisation/TROT/sourceofdata/SPORT/horseid/{}'
CHIP_INFO_URL = '{}pedigree/description/organisation/TROT/sourceofdata/SPORT/horseid/{}'
PEDIGREE_URL = '{}pedigree/organisation/TROT/sourceofdata/SPORT/horseid/{}?pedigreeTree=SMALL'
OFFSPRING_URL = '{}offspring/organisation/TROT/sourceofdata/SPORT/horseid/{}?genderCode={}'
RESULT_URL = '{}results/organisation/TROT/sourceofdata/SPORT/horseid/{}'
RESULT_SUMMARY_URL = '{}statistics/organisation/TROT/sourceofdata/SPORT/horseid/{}'


def handle_pedigree(pedigree):
    sire = ItemLoader(item=HorseItem())
    dam = ItemLoader(item=HorseItem())

    if 'father' in pedigree:

        sire.add_value('name', pedigree['father']['name'])
        sire.add_value('country', pedigree['father']['name'])
        sire.add_value('link', pedigree['father']['horseId'])
        sire.add_value('registration', pedigree['father']['registrationNumber'])
        sire.add_value('sex', 'horse')

        grand_sire, grand_dam = handle_pedigree(pedigree['father'])

        sire.add_value('sire', grand_sire)
        sire.add_value('dam', grand_dam)

    if 'mother' in pedigree:
        dam.add_value('name', pedigree['mother']['name'])
        dam.add_value('country', pedigree['mother']['name'])
        dam.add_value('link', pedigree['mother']['horseId'])
        dam.add_value('registration', pedigree['mother']['registrationNumber'])
        dam.add_value('sex', 'mare')

        grand_sire, grand_dam = handle_pedigree(pedigree['mother'])

        dam.add_value('sire', grand_sire)
        dam.add_value('dam', grand_dam)

    return sire.load_item() if sire.load_item() else None, dam.load_item() if dam.load_item() else None


def handle_racetime(timevalue):
    if timevalue > 9000:
        return 0

    minutes, timevalue = divmod(timevalue, 1000)
    seconds, timevalue = divmod(timevalue, 10)

    return minutes * 60 + seconds + timevalue / 10


class HorseCollector(Spider):
    """
    Collects horses from https://sportapp.travsport.se
    It takes a start_id as starting point.
    If the horse collected is a mare and it has offspring, all these are also collected.
    """
    name = 'horsecollector'
    allowed_domains = ['travsport.se']

    def __init__(self, start_id, *args, **kwargs):
        super(HorseCollector, self).__init__(*args, **kwargs)
        self.start_id = start_id


    def start_requests(self):
        yield JsonRequest(
                    url=BASIC_INFO_URL.format(BASE_URL, self.start_id),
                    callback=self.parse_basic_info)


    def parse_basic_info(self, response):
        response_json = json.loads(response.body)

        horse = ItemLoader(item = HorseItem())

        horse.add_value('name', response_json['name'])
        horse.add_value('country', response_json['birthCountryCode'])
        horse.add_value('breeder', response_json['breeder']['name'])
        horse.add_value('birthdate', response_json['dateOfBirth'])
        horse.add_value('link', response_json['id'])
        horse.add_value('registration', response_json['registrationNumber'])
        horse.add_value('sex', response_json['horseGender']['code'])
        horse.add_value('breed', response_json['horseBreed']['code'])

        if 'uelnNumber' in response_json:
            horse.add_value('ueln', response_json['uelnNumber'])

        yield JsonRequest(
                    url=CHIP_INFO_URL.format(BASE_URL, horse.get_output_value('link')),
                    callback=self.parse_chip,
                    cb_kwargs=dict(horse=horse),
                    meta={'has_offspring': response_json['offspringExists'],
                          'has_started': response_json['resultsExists'],
                          'gender_code': response_json['horseGender']['code']})


    def parse_chip(self, response, horse):
        response_json = json.loads(response.body)

        horse.add_value('chip', response_json.get('chipNumber'))

        yield JsonRequest(
                    url=PEDIGREE_URL.format(BASE_URL, horse.get_output_value('link')),
                    callback=self.parse_pedigree,
                    cb_kwargs=dict(horse=horse),
                    meta={'has_offspring': response.meta['has_offspring'],
                          'has_started': response.meta['has_started'],
                          'gender_code': response.meta['gender_code']})


    def parse_pedigree(self, response, horse):
        response_json = json.loads(response.body)

        sire, dam = handle_pedigree(response_json)

        if sire:
            horse.add_value('sire', sire)

        if dam:
            horse.add_value('dam', dam)

        if response.meta['has_offspring']:
            yield JsonRequest(
                        url=OFFSPRING_URL.format(BASE_URL, horse.get_output_value('link'), response.meta['gender_code']),
                        callback=self.parse_offspring,
                        cb_kwargs=dict(horse=horse),
                        meta={'has_started': response.meta['has_started']})

        elif response.meta['has_started']:
            yield JsonRequest(
                        url=RESULT_URL.format(BASE_URL, horse.get_output_value('link')),
                        callback=self.parse_results,
                        cb_kwargs=dict(horse=horse))

        else:
            yield horse.load_item()


    def parse_offspring(self, response, horse):
        response_json = json.loads(response.body)

        for offspring in response_json['offspring']:
            progeny = ItemLoader(item=HorseItem())

            progeny.add_value('name', offspring['horse']['name'])
            progeny.add_value('country', offspring['horse']['name'])
            progeny.add_value('birthdate', offspring['yearBorn'])
            progeny.add_value('link', offspring['horse']['id'])
            progeny.add_value('registration', offspring['registrationNumber'])
            progeny.add_value('sex', offspring['gender']['code'])

            if offspring['numberOfStarts']['sortValue'] is not None and offspring['numberOfStarts']['sortValue'] > 0:
                progeny.add_value('start_summary', {
                    'starts': offspring['numberOfStarts']['sortValue'],
                    'wins': offspring['firstPlaces'] if offspring['firstPlaces'] != '?' else 0,
                    'place': offspring['secondPlaces'] if offspring['secondPlaces'] != '?' else 0,
                    'show': offspring['thirdPlaces'] if offspring['thirdPlaces'] != '?' else 0,
                    'purse': offspring['prizeMoney']['sortValue'],
                    'standing': offspring['trotAdditionalInformation']['voltStartRecord']['displayValue'],
                    'auto': offspring['trotAdditionalInformation']['autoStartRecord']['displayValue']
                })

            if horse.get_output_value('sex') == 'mare':
                sire = ItemLoader(item=HorseItem())

                sire.add_value('name', offspring['horsesParent']['name'])
                sire.add_value('country', offspring['horsesParent']['name'])
                sire.add_value('link', offspring['horsesParent']['id'])
                sire.add_value('sex', 'horse')

                progeny.add_value('sire', sire.load_item())

                if not os.path.exists(os.path.join(JSON_DIRECTORY, 'horses', str(offspring['horse']['id']) + '.json')):
                    yield JsonRequest(
                                url=BASIC_INFO_URL.format(BASE_URL, offspring['horse']['id']),
                                callback=self.parse_basic_info)

            else:
                if offspring['horsesParent']['id'] != 0:
                    dam = ItemLoader(item=HorseItem())

                    dam.add_value('name', offspring['horsesParent']['name'])
                    dam.add_value('country', offspring['horsesParent']['name'])
                    dam.add_value('link', offspring['horsesParent']['id'])
                    dam.add_value('sex', 'mare')

                    if offspring['horsesParentsFather']['id'] != 0:
                        dam_sire = ItemLoader(item=HorseItem())

                        dam_sire.add_value('name', offspring['horsesParentsFather']['name'])
                        dam_sire.add_value('country', offspring['horsesParentsFather']['name'])
                        dam_sire.add_value('link', offspring['horsesParentsFather']['id'])
                        dam_sire.add_value('sex', 'horse')

                        dam.add_value('sire', dam_sire.load_item())

                    progeny.add_value('dam', dam.load_item())

            horse.add_value('offspring', progeny.load_item())

        if response.meta['has_started']:
            yield JsonRequest(
                        url=RESULT_URL.format(BASE_URL, horse.get_output_value('link')),
                        callback=self.parse_results,
                        cb_kwargs=dict(horse=horse))

        else:
            yield horse.load_item()


    def parse_results(self, response, horse):
        response_json = json.loads(response.body)

        for start_json in response_json:
            start = {
                'racetrack_code': start_json['trackCode'],
                'race_date': start_json['raceInformation']['date'],
                'racenumber': start_json['raceInformation'].get('raceNumber'),
                'race_id': start_json['raceInformation'].get('raceId'),
                'raceday_id': start_json['raceInformation'].get('raceDayId'),
                'post_position': start_json['startPosition'].get('sortValue'),
                'distance': start_json['distance'].get('sortValue'),
                'finish': start_json['placement'].get('sortValue'),
                'racetime': handle_racetime(start_json['kilometerTime'].get('sortValue')),
                'gallop': 'g' in start_json['kilometerTime'].get('displayValue'),
                'ev_odds': start_json['odds'].get('sortValue'),
                'driver': start_json['driver'].get('name'),
                'trainer': start_json['trainer'].get('name'),
                'start_method': {'V': 'standing', 'A': 'mobile', 'L': 'line'}[start_json['startMethod']],
                'purse': start_json['prizeMoney'].get('sortValue'),
                'started': not start_json['withdrawn'],
                'racetype': 'race',
                'disqualified': start_json['placement'].get('displayValue') == 'd',
                'monte': 'm' in start_json['raceType']['displayValue']
            }

            if start_json['kilometerTime'].get('displayValue'):
                start['dnf'] = start_json['kilometerTime']['displayValue'][0] == 'u'

            if start_json['raceType']['displayValue'] not in ['', 'r', 'm', 'b', 'bm']:
                start['racetype'] = {'k': 'qualifier', 'p': 'premium'}[start_json['raceType']['displayValue'][0]]

            if start['racetype'] == 'qualifier' and start['started']:
                start['approved'] = start_json['placement'].get('displayValue')[ : 2] == 'gdk'
            elif start['racetype'] == 'premium' and start['started']:
                start['approved'] = start_json['placement'].get('displayValue')[0] == 'p'

            if start['disqualified'] and start_json['kilometerTime'].get('displayValue') not in ['ug', 'uag']:
                start['disqstring'] = start_json['kilometerTime'].get('displayValue')
                if start['gallop']:
                    start['disqstring'] = start['disqstring'][ : -1 ]

                if start['start_method'] == 'mobile':
                    start['disqstring'] = start['disqstring'][ : -1 ]

            horse.add_value('starts', start)

        yield JsonRequest(
                    url=RESULT_SUMMARY_URL.format(BASE_URL, horse.get_output_value('link')),
                    callback=self.parse_result_summary,
                    cb_kwargs=dict(horse=horse))


    def parse_result_summary(self, response, horse):
        response_json = json.loads(response.body)

        for year in response_json['statistics']:
            if year['numberOfStarts'] == '0':
                continue

            wins, place, show = [int(x) if x.isnumeric() else 0 for x in year['placements'].split('-')]
            purse = int(year['prizeMoney'].replace(' ', '').replace('kr', ''))
            horse.add_value('start_summary', {
                'starts': year['numberOfStarts'],
                'wins': wins,
                'place': place,
                'show': show,
                'purse': purse,
                'mark': year.get('mark', None),
                'year': 0 if year['year'] == 'Livs' else int(year['year'])
            })

        yield horse.load_item()
