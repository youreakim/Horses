import scrapy
from itemloaders.processors import MapCompose, TakeFirst
from w3lib.html import remove_tags


def handle_name(name):
    if '(' in name:
        name = name[ : name.find('(') ]

    return name.replace('*', '')


def handle_country(name):
    if '(' in name:
        return name[ name.find('(') + 1 : name.find(')') ]

    return 'NO'


def handle_gender(gender):
    if gender in ['horse', 'mare', 'gelding', '']:
        return gender

    return {
        'hp': 'mare',
        'v': 'gelding',
        'kh': 'horse',
        'h': 'horse'
        }[gender]


def handle_breed(breed):
    return {
        'standardbred': 'standardbred',
        'coldblood': 'coldblood',
        'varmblods traver': 'standardbred',
        'kaldblods traver': 'coldblood'
        }[breed]


def handle_startmethod(method):
    return {
        'volt': 'standing',
        'auto': 'mobile',
        'mobile': 'mobile',
        'standing': 'standing',
        'linje': 'line'
    }[method]


def check_ueln(ueln):
    if len(ueln) == 15:
        return ueln


def handle_birthdate(birthdate):
    if len(birthdate) == 4 and birthdate.isdigit():
        return f'{birthdate}-01-01'

    elif len(birthdate) == 10 and len(birthdate.split('-')) == 3:
        return birthdate


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
    cancelled = scrapy.Field(
        output_processor = TakeFirst()
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
        output_processor = TakeFirst()
    )
    distance = scrapy.Field(
        output_processor = TakeFirst()
    )
    racetime = scrapy.Field(
        output_processor = TakeFirst()
    )
    driver = scrapy.Field(
        input_processor = MapCompose(handle_name, str.strip),
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
        input_processor = MapCompose(str.strip),
        output_processor = TakeFirst()
    )


class HorseItem(scrapy.Item):
    name = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.upper, handle_name, str.strip),
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
    country = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.upper, handle_country, str.strip),
        output_processor = TakeFirst()
    )
    birthdate = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_birthdate),
        output_processor = TakeFirst()
    )
    sex = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.lower, handle_gender),
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
        input_processor = MapCompose(remove_tags, str.strip),
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
    ueln = scrapy.Field(
        input_processor = MapCompose(check_ueln),
        output_processor=TakeFirst()
    )
    chip = scrapy.Field(
        output_processor=TakeFirst()
    )
