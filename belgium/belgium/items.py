import scrapy
from itemloaders.processors import MapCompose, TakeFirst, Join
from w3lib.html import remove_tags

import re


def handle_gender(gender):
    if gender == 'rien':
        return None

    if ',' in gender:
        gender = gender.replace(',', '').strip()

    if gender in ['gelding', 'horse', 'mare']:
        return gender

    return {
        'étalon': 'horse',
        'jument': 'mare',
        'hongre': 'gelding'
    }[gender]


def remove_country(name):
    if '(' in name:
        name = name[ : name.find('(') ]

    return name


def handle_startmethod(startmethod):
    if 'autostart' in startmethod:
        return 'mobile'

    return 'standing'


def handle_birthdate(date_string):
    if len(date_string) == 4 and date_string.isdigit():
        return f'{date_string}-01-01'

    if len(date_string) == 10:
        if date_string[4] == '-':
            return date_string

        return '-'.join(reversed(date_string.split('-')))


def is_monte(monte):
    return 'monté' in monte


def handle_racetime(time_string):
    time_splits = re.split(r'[\"\']', time_string)

    if len(time_splits) == 3:
        min, sec, hundreds = [int(x.strip()) for x in time_splits if x != '']

        return min * 60 + sec + hundreds / 100


def translate_country(country):
    return {
        'belgique': 'BE',
        'italie': 'IT',
        'france': 'FR',
        'états-unis': 'US',
        'pays-bas': 'NL',
        'suède': 'SE',
        'norvège': 'NO',
        'australie': 'AU',
        'autriche': 'AT',
        'danemark': 'DK',
        'estonie': 'EE',
        'finlande': 'FI',
        'allemagne': 'DE',
        'lettonie': 'LV',
        'lituanie': 'LT',
        'nouvelle-zélande': 'NZ',
        'russie': 'RU',
        'espagne': 'ES',
        'suisse': 'CH'
    }[country]


def did_start(place_string):
    return 'np' not in place_string.lower()


def was_disqualified(place_string):
    return 'd' in place_string.lower()


class RacedayItem(scrapy.Item):
    date = scrapy.Field(
        output_processor=TakeFirst()
    )
    racetrack = scrapy.Field(
        output_processor=TakeFirst()
    )
    racetrack_code = scrapy.Field(
        input_processor=MapCompose(str),
        output_processor=TakeFirst()
    )
    link = scrapy.Field(
        output_processor=TakeFirst()
    )
    races = scrapy.Field(
        input_processor=MapCompose(dict)
    )
    collection_date = scrapy.Field(
        output_processor=TakeFirst()
    )
    status = scrapy.Field(
        output_processor=TakeFirst()
    )


class RaceItem(scrapy.Item):
    conditions = scrapy.Field(
        output_processor = TakeFirst()
    )
    race_name = scrapy.Field(
        output_processor = TakeFirst()
    )
    distance = scrapy.Field(
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        output_processor = TakeFirst()
    )
    racenumber = scrapy.Field(
        input_processor = MapCompose(int),
        output_processor = TakeFirst()
    )
    monte = scrapy.Field(
        input_processor = MapCompose(is_monte),
        output_processor = TakeFirst()
    )
    startmethod = scrapy.Field(
        input_processor = MapCompose(str.lower, handle_startmethod),
        output_processor = TakeFirst()
    )
    racetype = scrapy.Field(
        output_processor = TakeFirst()
    )
    status = scrapy.Field(
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        output_processor = TakeFirst()
    )
    starters = scrapy.Field(
        input_processor = MapCompose(dict)
    )


class RaceStarterItem(scrapy.Item):
    horse = scrapy.Field(
        input_processor=MapCompose(dict),
        output_processor=TakeFirst()
    )
    finish = scrapy.Field(
        output_processor = TakeFirst()
    )
    order = scrapy.Field(
        output_processor = TakeFirst()
    )
    startnumber = scrapy.Field(
        output_processor = TakeFirst()
    )
    distance = scrapy.Field(
        output_processor = TakeFirst()
    )
    racetime = scrapy.Field(
        input_processor = MapCompose(handle_racetime),
        output_processor = TakeFirst()
    )
    driver = scrapy.Field(
        input_processor = MapCompose(str.strip),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        output_processor = TakeFirst()
    )
    odds = scrapy.Field(
        output_processor = TakeFirst()
    )
    ev_odds = scrapy.Field(
        output_processor = TakeFirst()
    )
    show_odds = scrapy.Field(
        output_processor = TakeFirst()
    )
    gallop = scrapy.Field(
        output_processor = TakeFirst()
    )
    dnf = scrapy.Field(
        output_processor = TakeFirst()
    )
    approved = scrapy.Field(
        output_processor = TakeFirst()
    )
    started = scrapy.Field(
        input_processor = MapCompose(did_start),
        output_processor = TakeFirst()
    )
    disqualified = scrapy.Field(
        input_processor = MapCompose(was_disqualified),
        output_processor = TakeFirst()
    )
    disqstring = scrapy.Field(
        output_processor = TakeFirst()
    )
    postposition = scrapy.Field(
        output_processor = TakeFirst()
    )
    trainer = scrapy.Field(
        input_processor = MapCompose(str.strip),
        output_processor = TakeFirst()
    )


class HorseItem(scrapy.Item):
    name = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_country, str.strip, str.upper),
        output_processor=TakeFirst()
    )
    link = scrapy.Field(
        input_processor=MapCompose(remove_tags),
        output_processor=TakeFirst()
    )
    country = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.lower, translate_country),
        output_processor = TakeFirst()
    )
    birthdate = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_birthdate),
        output_processor = TakeFirst()
    )
    sex = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.lower, handle_gender),
        output_processor = TakeFirst()
    )
    sire = scrapy.Field(
        input_processor = MapCompose(dict),
        output_processor = TakeFirst()
    )
    dam = scrapy.Field(
        input_processor = MapCompose(dict),
        output_processor = TakeFirst()
    )
    registration = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
    breed = scrapy.Field(
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
        input_processor = MapCompose(str.strip),
        output_processor = Join(separator=', ')
    )
    ueln = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor=TakeFirst()
    )
    chip = scrapy.Field(
        output_processor=TakeFirst()
    )
