import scrapy
from itemloaders.processors import MapCompose, Compose, TakeFirst, Join

import re

def clean_name(name):
    return name.translate(str.maketrans({'`': "'", '†': None, '*': None}))


def handle_sex(sex):
    return {
        'S': 'mare',
        'H': 'horse',
        'V': 'gelding',
        'stallion': 'horse',
        'gelding': 'gelding',
        'mare': 'mare',
        'horse': 'horse'
    }[sex]


def handle_name(name_string):
    if '(' not in name_string:
        return name_string

    return name_string[ : name_string.find('(') ]


def handle_country(name_string):
    if len(name_string) == 2:
        return name_string

    if '(' in name_string:
        return name_string[ name_string.find('(') + 1 : -1 ]

    return 'SE'


def handle_breed(breed):
    if len(breed) == 1:
        return {
            'V': 'standardbred',
            'K': 'coldblood'
        }[breed]

    if 'varmblod' in breed.lower():
        return 'standardbred'
    elif 'kallblod' in breed.lower():
        return 'coldblood'


def handle_birthdate(date_string):
    if re.match(r'\d{4}-\d{2}-\d{2}', date_string):
        return date_string

    elif len(date_string) == 4 and date_string.isdigit():
        return f'{date_string}-01-01'


def handle_racetime(timevalue):
    if isinstance(timevalue, str):
        if ',' in timevalue:
            timevalue = int(''.join([x for x in timevalue if x.isdigit()])) + 1000
        elif timevalue.isdigit():
            timevalue = int(timevalue)
        else:
            return 0

    elif isinstance(timevalue, float):
        return timevalue

    if timevalue > 9000:
        return 0

    minutes, timevalue = divmod(timevalue, 1000)
    seconds, timevalue = divmod(timevalue, 10)

    return minutes * 60 + seconds + timevalue / 10


def is_monte(conditions):
    return 'montélopp' in conditions.lower()


def handle_startmethod(conditions):
    if conditions in ['volte', 'auto', 'line']:
        return {'volte': 'standing',
                'auto': 'mobile',
                'line': 'line'}[conditions]

    if 'autostart' in conditions.lower():
            return 'mobile'

    return 'standing'


def handle_racetype(code):
    if code in ['race', 'qualifier', 'premium']:
        return code

    if len(code) == 1:
        return {'V': 'race', 'K': 'qualifier', 'P': 'premium'}[code]

    if '\n' in code:
        if 'kvallopp' in code.lower():
            return 'qualifier'
        elif 'premielopp' in code.lower():
            return 'premium'
        else:
            return 'race'



def remove_licence(name):
    if name[-2] == ' ' and name[-1].islower():
        return name[ : -2 ]

    return name


def get_distance(distance_string):
    if isinstance(distance_string, int):
        return distance_string

    if distance_string.isdigit():
        return int(distance_string)

    if '/' in distance_string:
        return int(distance_string.split('/')[1])

    match = re.search(r'(\d{4}) m', distance_string)

    if match:
        return int(match.group(1))


def handle_postposition(postposition):
    if isinstance(postposition, int):
        return postposition

    if '/' in postposition:
        return int(postposition.split('/')[0])


def is_disqualified(value):
    if isinstance(value, bool):
        return value

    return 'd' in value and 'dist' not in value


def did_not_finish(time_string):
    return 'u' in time_string.replace('kub', '') or 'vänd' in time_string


def handle_finish(place):
    return place if place.isdigit() else 0


def is_approved(place):
    if 'g' in place:
        return 'gdk' in place
    elif 'p' in place:
        return 'ej' not in place


def did_gallop(time_string):
    if isinstance(time_string, bool):
        return time_string

    return 'g' in time_string


def handle_odds(odds):
    if isinstance(odds, str):
        if '(' in odds:
            return int(odds.strip()[ 1 : -1 ])
        elif ',' in odds:
            return float(odds.replace(',', '.'))

    return odds


def calculate_ev_odds(ev_odds):
    if isinstance(ev_odds, float):
        return int(odds * 10)

    return ev_odds


def filter_breeder(breeder):
    if breeder != 'uppgift saknas':
        return breeder


class RacedayItem(scrapy.Item):
    date = scrapy.Field(
        output_processor = TakeFirst()
    )
    racetrack = scrapy.Field(
        output_processor = TakeFirst()
    )
    racetrack_code = scrapy.Field(
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
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
        output_processor = Join(separator='\n')
    )
    distance = scrapy.Field(
        input_processor = MapCompose(get_distance),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        output_processor = TakeFirst()
    )
    racenumber = scrapy.Field(
        output_processor = TakeFirst()
    )
    monte = scrapy.Field(
        input_processor = MapCompose(is_monte),
        output_processor = TakeFirst()
    )
    startmethod     = scrapy.Field(
        input_processor = MapCompose(handle_startmethod),
        output_processor = TakeFirst()
    )
    racetype = scrapy.Field(
        input_processor = MapCompose(handle_racetype),
        output_processor = TakeFirst()
    )
    status = scrapy.Field(
        output_processor = TakeFirst()
    )
    link = scrapy.Field(#
        output_processor = TakeFirst()
    )
    starters = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    racename = scrapy.Field(
        output_processor = TakeFirst()
    )
    track_condition = scrapy.Field(
        output_processor = TakeFirst()
    )


class RaceStarterItem(scrapy.Item):
    horse = scrapy.Field(
        input_processor = MapCompose(dict),
        output_processor = TakeFirst()
    )
    finish = scrapy.Field(
        input_processor = MapCompose(handle_finish),
        output_processor = TakeFirst()
    )
    order = scrapy.Field(
        output_processor = TakeFirst()
    )
    startnumber = scrapy.Field(
        input_processor = MapCompose(int),
        output_processor = TakeFirst()
    )
    distance = scrapy.Field(
        input_processor = MapCompose(get_distance),
        output_processor = TakeFirst()
    )
    racetime = scrapy.Field(
        input_processor = MapCompose(handle_racetime),
        output_processor = TakeFirst()
    )
    driver = scrapy.Field(
        input_processor = MapCompose(remove_licence),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        output_processor = TakeFirst()
    )
    odds = scrapy.Field(
        input_processor = MapCompose(handle_odds),
        output_processor = TakeFirst()
    )
    ev_odds = scrapy.Field(
        input_processor = MapCompose(handle_odds, calculate_ev_odds),
        output_processor = TakeFirst()
    )
    show_odds = scrapy.Field(
        input_processor = MapCompose(handle_odds),
        output_processor = TakeFirst()
    )
    gallop = scrapy.Field(
        input_processor = MapCompose(did_gallop),
        output_processor = TakeFirst()
    )
    dnf = scrapy.Field(
        input_processor = MapCompose(did_not_finish),
        output_processor = TakeFirst()
    )
    approved = scrapy.Field(
        input_processor = MapCompose(is_approved),
        output_processor = TakeFirst()
    )
    started = scrapy.Field(
        output_processor = TakeFirst()
    )
    disqualified = scrapy.Field(
        input_processor = MapCompose(is_disqualified),
        output_processor = TakeFirst()
    )
    disqstring = scrapy.Field(
        output_processor = TakeFirst()
    )
    postposition = scrapy.Field(
        input_processor = MapCompose(handle_postposition),
        output_processor = TakeFirst()
    )
    trainer = scrapy.Field(
        input_processor = MapCompose(remove_licence),
        output_processor = TakeFirst()
    )


class HorseItem(scrapy.Item):
    name = scrapy.Field(
        input_processor = MapCompose(handle_name, clean_name, str.strip, str.upper),
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        output_processor = TakeFirst()
    )
    country = scrapy.Field(
        input_processor = MapCompose(handle_country),
        output_processor = TakeFirst()
    )
    birthdate = scrapy.Field(
        input_processor = MapCompose(str, handle_birthdate),
        output_processor = TakeFirst()
    )
    sex = scrapy.Field(
        input_processor = MapCompose(handle_sex),
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
        input_processor = MapCompose(handle_breed),
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
        input_processor = MapCompose(filter_breeder),
        output_processor = TakeFirst()
    )
    ueln = scrapy.Field(
        output_processor = TakeFirst()
    )
    chip = scrapy.Field(
        output_processor = TakeFirst()
    )
