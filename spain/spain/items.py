import scrapy
from itemloaders.processors import MapCompose, TakeFirst, Join
from w3lib.html import remove_tags

from datetime import datetime


def convert_date(date):
    return datetime.strptime(date, '%d-%m-%Y').strftime('%Y-%m-%d')


def handle_birthdate(date_string):
    if date_string.isdigit() and len(date_string) < 3:
        current_year = datetime.today().year
        return f'{current_year - int(date_string)}-01-01'

    if date_string.isdigit() and len(date_string) == 4:
        return f'{date_string}-01-01'

    if '/' in date_string:
        date_splits = [''.join([z for z in x if z.isdigit()]) for x in date_string.split('/')]
        return '-'.join(reversed(date_splits))

    if '-' in date_string:
        return date_string


def convert_date_to_string(date):
    return date.strftime('%Y-%m-%d')


def handle_startmethod(start):
    return 'mobile' if 'Autostart' in start else 'standing'


def handle_distance(dist):
    if dist.isdigit():
        return dist

    if 'Distancia' in dist:
        dist = dist[ dist.find('Distancia') + len('Distancia') : ]


    return dist.replace('.', '').replace('m', '')


def handle_purse(purse):
    if isinstance(purse, int):
        return purse

    purse = purse.replace('€', '').replace('.', '').strip()

    if not purse.isdigit():
        return 0

    return int(purse)


def handle_racetime(time):
    time_splits = [int(x) for x in time.split("'") if x.strip().isdigit()]

    if len(time_splits) == 0:
        return 0

    return time_splits[0] * 60 + time_splits[1] + time_splits[2] / 10


def handle_horse_link(link):
    if '&' in link:
        link = link[ : link.find('&') ]

    if 'id=' in link:
        link = link[ link.find('id=') + 3 : ]

    if 'idcaballo' in link:
        link = link[ link.rfind('=') + 1 : ]

    return link


def handle_name(name):
    if '(' in name:
        name = name[ : name.find('(') ]

    return name


def handle_country(name):
    if '(' in name:
        return name[ name.find('(') + 1 : name.find(')') ]

    return 'ES'


def handle_racetrack(racetrack):
    if 'Hipòdrom ' in racetrack:
        racetrack = racetrack[ len('Hipòdrom ') : ]

        if racetrack[ : 3 ] == 'de ':
            racetrack   = racetrack[ 3 : ]

    return racetrack


def handle_sex(sex):
    if sex in ['horse', 'mare', 'gelding']:
        return sex

    return {'Macho': 'horse',
            'Caballo Castrado': 'gelding',
            'Macho Castrado': 'gelding',
            'Castrado': 'gelding',
            'Hembra': 'mare',
            'M': 'horse',
            'H': 'mare',
            'C': 'gelding',}[sex]


def handle_finish(finish):
    if '.' in finish:
        return int(finish.replace('.', ''))

    return 0


def get_racenumber(num_string):
    if num_string.isdigit():
        return num_string

    if '-' in num_string:
        return num_string[ : num_string.find('-') ].strip()


def get_race_id(link):
    return link[ link.find('id=') + 3 : link.find('&pagina') ]


def get_raceday_id(link):
    if link.isdigit():
        return link

    return link[ link.find('=') + 1 : ]


def did_start(place_string):
    return 'R' not in place_string


def is_disqualified(place_string):
    return 'D' in place_string


class RacedayItem(scrapy.Item):
    date = scrapy.Field(
        input_processor = MapCompose(str.strip),
        output_processor = TakeFirst()
    )
    racetrack = scrapy.Field(
        input_processor = MapCompose(str.strip, handle_racetrack),
        output_processor = TakeFirst()
    )
    racetrack_code = scrapy.Field(
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(get_raceday_id),
        output_processor = TakeFirst()
    )
    races = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    collection_date = scrapy.Field(
        input_processor = MapCompose(convert_date_to_string),
        output_processor = TakeFirst()
    )
    status = scrapy.Field(
        output_processor = TakeFirst()
    )


class RaceItem(scrapy.Item):
    conditions = scrapy.Field(
        input_processor = MapCompose(str.strip),
        output_processor = TakeFirst()
    )
    distance = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_distance, int),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        input_processor = MapCompose(handle_purse),
        output_processor = TakeFirst()
    )
    racenumber = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, get_racenumber, int),
        output_processor = TakeFirst()
    )
    monte = scrapy.Field(
        output_processor = TakeFirst()
    )
    startmethod = scrapy.Field(
        input_processor = MapCompose(str.strip, handle_startmethod),
        output_processor = TakeFirst()
    )
    racetype = scrapy.Field(
        output_processor = TakeFirst()
    )
    status = scrapy.Field(
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(get_race_id),
        output_processor = TakeFirst()
    )
    starters = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    racename = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = TakeFirst()
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
        input_processor = MapCompose(remove_tags, str.strip, int),
        output_processor = TakeFirst()
    )
    distance = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_distance, int),
        output_processor = TakeFirst()
    )
    racetime = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_racetime),
        output_processor = TakeFirst()
    )
    driver = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = TakeFirst()
    )
    trainer = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_purse),
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
        input_processor = MapCompose(remove_tags, did_start),
        output_processor = TakeFirst()
    )
    disqualified = scrapy.Field(
        input_processor = MapCompose(remove_tags, is_disqualified),
        output_processor = TakeFirst()
    )
    disqstring = scrapy.Field(
        output_processor = TakeFirst()
    )
    postposition = scrapy.Field(
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
        input_processor = MapCompose(remove_tags, str.strip, handle_birthdate),
        output_processor = TakeFirst()
    )
    sex = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_sex),
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
    race = scrapy.Field(
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
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = TakeFirst()
    )
    ueln = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
    chip = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
