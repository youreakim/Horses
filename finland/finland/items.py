import scrapy
from itemloaders.processors import MapCompose, TakeFirst, Join
from w3lib.html import remove_tags

import datetime
import re


# RacedayItem
def parse_date(date_string):
    if '.' in date_string:
        date_string = date_string.split('\xa0')[1].strip()
        return datetime.datetime.strptime(date_string, '%d.%m.%Y').strftime('%Y-%m-%d')

    return date_string


def find_code(url):
    if 'RaceResults' in url:
        return url[ url.rfind('&sp=') + 4 : ]

    return url[ url.find('&sp', url.find('&sp') + 1) + 4 : url.rfind('&sp') ]


def shorten_link(link):
    return link[ link.find('&sp=') + 4 :]


def get_racetrack(racetrack):
    if ' , ' in racetrack:
        return racetrack.split(' , ')[0]

    return racetrack


# RaceItem
def find_racenumber(url):
    return url[ url.rfind('C') + 1 : ]


def find_racetype(conditions):
    racetypes = {
        'lähtö': 'race',
        'koelähtö': 'koe',
        'opetuslähtö': 'opetus',
        'nuoret-lähtö': 'nuoret'
        }

    for racetype in racetypes:
        if racetype in conditions:
            return racetypes[racetype]


def is_monte(conditions):
    return 'monte' in conditions.lower()


def find_startmethod(conditions):
    startmethods = {
        'tasoitusajo': 'standing',
        'ryhmäajo': 'mobile',
        'linjalähtö': 'line'
        }

    for startmethod in startmethods:
        if startmethod in conditions:
            return startmethods[startmethod]


def get_distance(conditions):
    matches = re.search(r' (\d{4}) m ', conditions)

    if matches:
        return matches.group(1)


def calculate_purse(conditions):
    if conditions[-1] != ')':
        return 0

    return sum(int(x) for x in conditions[ conditions.rfind('(') + 1 : -1 ].split('-'))


def shorten_conditions(conditions):
    match = re.search(r'\d{2}:\d{2}', conditions)

    if match:
        return conditions[ conditions.find(':') + 3 : ]

    return conditions


# RaceStarterItem
def handle_time(time_string):
    if ',' in time_string and len(time_string) == 4:
        return float(time_string.replace(',', '.')) + 60

    elif len(time_string) == 6 and '.' in time_string:
        time_splits = time_string.split('.')
        return int(time_splits[0]) * 60 + int(time_splits[1]) + int(time_splits[2]) / 10


def has_galloped(disqstring):
    return 'x' in disqstring


def handle_finish(place_string):
    if '(' in place_string:
        place_string = place_string[ : place_string.find('(') ].strip()

    if '.' in place_string:
        return int(place_string.replace('.', ''))

    return 0


def handle_dist(dpp_string):
    if dpp_string.isdigit() and len(dpp_string) == 4:
        return dpp_string

    elif ':' in dpp_string:
        return dpp_string.split(':')[0]


def get_pp(dpp_string):
    if ':' in dpp_string:
        return dpp_string.split(':')[1]

    elif dpp_string.isdigit():
        return dpp_string


def clean(disqstring):
    return disqstring.replace('\xa0', '')


def handle_odds(odds_string):
    if odds_string.isdigit():
        return odds_string

    elif ',' in odds_string:
        return odds_string.replace(',', '.')


def handle_purse(purse_string):
    purse_string = purse_string.replace('€', '').replace(' ', '')
    if purse_string.isdigit():
        return purse_string


# HorseItem
def parse_horse_link(link):
    return link[ link.rfind('?') + 5 : link.rfind('&') ]


def handle_sex(str):
    if str in ['gelding', 'horse', 'mare']:
        return str

    return {
        'r': 'gelding',
        't': 'mare',
        'o': 'horse',
        'ruuna': 'gelding',
        'tamma': 'mare',
        'ori': 'horse'
    }[str]


def handle_country(name):
    countries = {
        'ranska': 'FR',
        'suomi': 'FI',
        'ruotsi': 'SE',
        'yhdysvallat': 'US',
        'kanada': 'CA',
        'norja': 'NO',
        'tanska': 'DK',
        'saksa': 'DE',
        #'': 'BE',
        'italia': 'IT',
        #'': 'NL',
        #'': 'NZ',
        #'': 'AU',
        #'': 'RU',
        'espanja': 'ES',
        #'': 'CH',
    }

    if len(name) == 2:
        return name

    if name.lower() in countries:
        return countries[name.lower()]

    if '(' in name:
        return name[ name.find('(') + 1 : name.find(')')]

    return 'FI'


def handle_horse_link(link):
    if len(link) == 19 and link.isdigit():
        return link

    return link[ link.find('?sp=l') + 5 : link.find('&sp') ]


def handle_breed(str):
    if str in ['coldblood', 'standardbred', 'thoroughbred']:
        return str

    return {
        'lämminverinen': 'standardbred',
        'suomenhevonen': 'coldblood',
        'kylmäverinen': 'coldblood'
    }[str]


def handle_name(name):
    if '(' in name:
        name = name[ : name.find('(') ]

    return name.replace('*', '')


def handle_birthdate(birthdate):
    if birthdate.isdigit() and len(birthdate) == 4:
        return f'{birthdate}-01-01'

    elif len(birthdate.split('-')) == 3 and len(birthdate) == 12:
        return birthdate

    elif '.' in birthdate:
        return '-'.join(reversed(birthdate.split('.')))


def filter_ueln(ueln):
    if len(ueln) == 15:
        return ueln


class RacedayItem(scrapy.Item):
    date = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, parse_date),
        output_processor = TakeFirst()
    )
    racetrack = scrapy.Field(
        input_processor = MapCompose(remove_tags, get_racetrack, str.strip),
        output_processor = TakeFirst()
    )
    racetrack_code = scrapy.Field(
        input_processor = MapCompose(find_code),
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(shorten_link),
        output_processor = TakeFirst()
    )
    races = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    collection_date = scrapy.Field(
        output_processor = TakeFirst()
    )
    status = scrapy.Field(
        output_processor = TakeFirst()
    )

class RaceItem(scrapy.Item):
    conditions = scrapy.Field(
        input_processor = MapCompose(remove_tags, shorten_conditions, str.strip),
        output_processor = TakeFirst()
    )
    distance = scrapy.Field(
        input_processor = MapCompose(remove_tags, get_distance, int),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        input_processor = MapCompose(remove_tags, calculate_purse),
        output_processor = TakeFirst()
    )
    racenumber = scrapy.Field(
        input_processor = MapCompose(find_racenumber, int),
        output_processor = TakeFirst()
    )
    monte = scrapy.Field(
        input_processor = MapCompose(remove_tags, is_monte),
        output_processor = TakeFirst()
    )
    startmethod = scrapy.Field(
        input_processor = MapCompose(remove_tags, find_startmethod),
        output_processor = TakeFirst()
    )
    racetype = scrapy.Field(
        input_processor = MapCompose(remove_tags, find_racetype),
        output_processor = TakeFirst()
    )
    status = scrapy.Field(
        output_processor = TakeFirst()
    )
    link = scrapy.Field(#
        input_processor = MapCompose(shorten_link),
        output_processor = TakeFirst()
    )
    starters = scrapy.Field(
        input_processor = MapCompose(dict)
    )

class RaceStarterItem(scrapy.Item):
    horse = scrapy.Field(
        input_processor = MapCompose(dict),
        output_processor = TakeFirst()
    )
    finish = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_finish),
        output_processor = TakeFirst()
    )
    order = scrapy.Field(
        output_processor = TakeFirst()
    )
    startnumber = scrapy.Field(
        input_processor = MapCompose(remove_tags, int),
        output_processor = TakeFirst()
    )
    distance = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_dist, int),
        output_processor = TakeFirst()
    )
    racetime = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_time),
        output_processor = TakeFirst()
    )
    driver = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_name, str.strip),
        output_processor = TakeFirst()
    )
    trainer = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_name, str.strip),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_purse, int),
        output_processor = TakeFirst()
    )
    odds = scrapy.Field(
        input_processor = MapCompose(handle_odds, float),
        output_processor = TakeFirst()
    )
    ev_odds = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_odds, int),
        output_processor = TakeFirst()
    )
    show_odds = scrapy.Field(
        input_processor = MapCompose(handle_odds, float),
        output_processor = TakeFirst()
    )
    gallop = scrapy.Field(
        input_processor = MapCompose(remove_tags, has_galloped),
        output_processor = TakeFirst()
    )
    dnf = scrapy.Field(
        output_processor = TakeFirst()
    )
    approved = scrapy.Field(
        output_processor = TakeFirst()
    )
    started = scrapy.Field(
        output_processor = TakeFirst()
    )
    disqualified = scrapy.Field(
        output_processor = TakeFirst()
    )
    disqstring = scrapy.Field(
        input_processor = MapCompose(remove_tags, clean, str.strip),
        output_processor = TakeFirst()
    )
    postposition = scrapy.Field(
        input_processor = MapCompose(remove_tags, get_pp, int),
        output_processor = TakeFirst()
    )

class HorseItem(scrapy.Item):
    name = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_name, str.upper, str.strip),
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(handle_horse_link),
        output_processor = TakeFirst()
    )
    country = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_country),
        output_processor = TakeFirst()
    )
    birthdate = scrapy.Field(
        input_processor = MapCompose(str, handle_birthdate),
        output_processor = TakeFirst()
    )
    sex = scrapy.Field(
        input_processor = MapCompose(str.strip, str.lower, handle_sex),
        output_processor = TakeFirst()
    )
    sire = scrapy.Field(
        output_processor = TakeFirst(),
        input_processor = MapCompose(dict)
    )
    dam = scrapy.Field(
        input_processor = MapCompose(dict),
        output_processor = TakeFirst()
    )
    registration = scrapy.Field(
        output_processor = TakeFirst()
    )
    breed = scrapy.Field(
        input_processor = MapCompose(str.strip, str.lower, handle_breed),
        output_processor = TakeFirst()
    )
    offspring = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    start_summary = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    starts = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    breeder = scrapy.Field(
        output_processor = TakeFirst()
    )
    chip = scrapy.Field(
        output_processor = TakeFirst()
    )
    ueln = scrapy.Field(
        input_processor = MapCompose(filter_ueln),
        output_processor = TakeFirst()
    )
