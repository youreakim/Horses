import scrapy
import re
from itemloaders.processors import MapCompose, TakeFirst, Join
from w3lib.html import remove_tags
from datetime import date


def handle_purse(purse):
    purse = purse.replace('€', '').replace(' ', '').strip()
    return int(purse) if purse.isnumeric() else 0


def remove_racenumber(text):
    if '-' in text:
        return text[ text.find('-') + 1 : ].strip()
    return text


def get_distance(dist_string):
    distance = re.search(r'(\d\ ?\d\d\d)m?', dist_string)
    if distance:
        distance = distance.group(1).replace(' ', '').strip()
        return int(distance)


def is_monte(monte):
    return 'Monté' in monte


def parse_horse_link(link):
    link_parts = link.split('/')

    if len(link_parts) == 2:
        return link

    index = link_parts.index('fiche-cheval')
    return '/'.join(link_parts[ index + 1 : index + 3 ])


def handle_time(time):
    if time == '':
        return 0

    time_splits = [int(x) for x in re.split('[\'\"]', time)]

    return time_splits[0] * 60 + time_splits[1] + time_splits[2] / 10


def handle_sex(sex):
    if sex in ['horse', 'mare', 'gelding']:
        return sex

    return {'M': 'horse',
            'F': 'mare',
            'H': 'gelding'}[sex]


def handle_country(name):
    # country codes not always ISO-3166
    # default assumption is that the horse is french
    # the first letter in a french horses name tells which year it is born,
    # so if a horse named 'A....' is not born in the year 1900 + x * 22
    # it is not french
    if '(' in name:
        return name[ name.find('(') + 1 : name.find(')')]

    return 'FR'


def handle_name(name):
    if '(' in name:
        return name[ : name.find('(')]

    return name


def handle_birthdate(date_string):
    if date_string.isdigit() and len(date_string) == 4:
        return date_string + '-01-01'

    elif date_string.isdigit() and len(date_string) == 1:
        return str(date.today().year - int(date_string)) + '-01-01'


def get_raceday_date(link):
    return link.split('/')[-2]


def get_racetrack_code(link):
    return link.split('/')[-1]


def shorten_raceday_link(link):
    return link.split('/')[-2:]


def shorten_race_link(link):
    return link.split('/')[ -5 : -2 ]


def get_racenumber(link):
    return link.split('/')[-3]


def get_startmethod(conditions):
    return 'mobile' if "Départ à l'autostart" in conditions else 'standing'


class RacedayItem(scrapy.Item):
    date = scrapy.Field(
        input_processor = MapCompose(get_raceday_date),
        output_processor = TakeFirst()
    )
    racetrack = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = TakeFirst()
    )
    racetrack_code = scrapy.Field(
        input_processor = MapCompose(get_racetrack_code),
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(shorten_raceday_link),
        output_processor = Join(separator = '/')
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
        input_processor = MapCompose(remove_tags),
        output_processor = Join(separator = '\n')
    )
    distance = scrapy.Field(
        input_processor = MapCompose(remove_tags, get_distance),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_purse),
        output_processor = TakeFirst()
    )
    racenumber = scrapy.Field(
        input_processor = MapCompose(get_racenumber, int),
        output_processor = TakeFirst()
    )
    monte = scrapy.Field(
        input_processor = MapCompose(remove_tags, is_monte),
        output_processor = TakeFirst()
    )
    startmethod = scrapy.Field(
        input_processor = MapCompose(remove_tags, get_startmethod),
        output_processor = TakeFirst()
    )
    racetype = scrapy.Field(
        output_processor = TakeFirst()
    )
    status = scrapy.Field(
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(shorten_race_link),
        output_processor = Join(separator='/')
    )
    starters = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    racename = scrapy.Field(
        input_processor = MapCompose(remove_tags, remove_racenumber),
        output_processor = TakeFirst()
    )

class RaceStarterItem(scrapy.Item):
    horse = scrapy.Field(
        input_processor = MapCompose(dict),
        output_processor = TakeFirst()
    )
    finish = scrapy.Field(
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
        input_processor = MapCompose(remove_tags, get_distance),
        output_processor = TakeFirst()
    )
    racetime = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_time),
        output_processor = TakeFirst()
    )
    driver = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_purse),
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
        output_processor = TakeFirst()
    )
    disqualified = scrapy.Field(
        output_processor = TakeFirst()
    )
    disqstring = scrapy.Field(
        output_processor = TakeFirst()
    )
    postposition = scrapy.Field(
        output_processor = TakeFirst()
    )
    trainer = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = TakeFirst()
    )

class HorseItem(scrapy.Item):
    name = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_name, str.strip, str.upper),
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(parse_horse_link),
        output_processor = TakeFirst()
    )
    country = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_country, str.strip, str.upper),
        output_processor = TakeFirst()
    )
    birthdate = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_birthdate),
        output_processor = TakeFirst()
    )
    sex = scrapy.Field(
        input_processor = MapCompose(str.strip, handle_sex),
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
    chip = scrapy.Field(
        output_processor = TakeFirst()
    )
    ueln = scrapy.Field(
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
        input_processor = MapCompose(remove_tags, str.upper),
        output_processor = TakeFirst()
    )
    collection_date = scrapy.Field(
        output_processor = TakeFirst()
    )
    collection_date = scrapy.Field(
        output_processor = TakeFirst()
    )
