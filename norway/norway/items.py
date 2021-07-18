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
        'h': 'horse',
        'hingst': 'horse',
        'hoppe': 'mare',
        'vallak': 'gelding'
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


def handle_race_purse(conditions):
    if 'Premier: ' in conditions:
        purse_string = conditions[ conditions.find('Premier: ') + 9 : conditions.find(' kr.', conditions.find('Premier: '))]

        return sum(int(''.join(y for y in x if y.isnumeric())) for x in purse_string.split('-'))


def check_ueln(ueln):
    if len(ueln) == 15:
        return ueln


def handle_birthdate(birthdate):
    if len(birthdate) == 4 and birthdate.isdigit():
        return f'{birthdate}-01-01'

    elif len(birthdate) == 10 and len(birthdate.split('-')) == 3:
        return birthdate


def handle_mark(mark):
    mark = mark.replace('a', '').replace(',', '.').strip()

    if len(mark) == 4:
        return float(mark)


def did_gallop(time_string):
    return 'g' in time_string


def did_not_finish(time_string):
    return 'br' in time_string


def is_disqualified(time_string):
    return 'd' in time_string


def handle_racetime(time_string):
    if time_string.lower() == 'str':
        return None

    if ',' in time_string:
        return float(time_string.replace('a', '').replace('r', '').replace('g', '').replace(',', '.'))


def handle_disqualification(time_string):
    if 'd' in time_string:
        return time_string.replace('a', '').replace('d', '').replace('g', '').replace('br', '')


def did_start(time_string):
    return time_string.lower() != 'str'


def handle_racetype(time_string):
    if 'P' in time_string:
        return 'qualifier'

    elif time_string.isnumeric():
        return 'race'


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
        input_processor=MapCompose(handle_race_purse),
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
        input_processor=MapCompose(handle_racetime),
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
        input_processor=MapCompose(did_gallop),
        output_processor = TakeFirst()
    )
    dnf = scrapy.Field(
        input_processor=MapCompose(did_not_finish),
        output_processor = TakeFirst()
    )
    approved = scrapy.Field(
        output_processor = TakeFirst()
    )
    started = scrapy.Field(
        output_processor = TakeFirst()
    )
    disqualified = scrapy.Field(
        input_processor=MapCompose(is_disqualified),
        output_processor = TakeFirst()
    )
    disqstring = scrapy.Field(
        input_processor=MapCompose(handle_disqualification, str.strip),
        output_processor = TakeFirst()
    )
    postposition = scrapy.Field(
        output_processor = TakeFirst()
    )
    trainer = scrapy.Field(
        input_processor = MapCompose(handle_name, str.strip),
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
    collection_date = scrapy.Field(
        output_processor=TakeFirst()
    )


class SummaryItem(scrapy.Item):
    year = scrapy.Field(
        output_processor=TakeFirst()
    )
    starts = scrapy.Field(
        output_processor=TakeFirst()
    )
    wins = scrapy.Field(
        output_processor=TakeFirst()
    )
    seconds = scrapy.Field(
        output_processor=TakeFirst()
    )
    thirds = scrapy.Field(
        output_processor=TakeFirst()
    )
    mobile_mark = scrapy.Field(
        input_processor=MapCompose(handle_mark),
        output_processor=TakeFirst()
    )
    standing_mark = scrapy.Field(
        input_processor=MapCompose(handle_mark),
        output_processor=TakeFirst()
    )
    purse = scrapy.Field(
        output_processor=TakeFirst()
    )


class RacelineItem(scrapy.Item):
    date = scrapy.Field(
        output_processor=TakeFirst()
    )
    link = scrapy.Field(
        output_processor=TakeFirst()
    )
    racetrack = scrapy.Field(
        output_processor=TakeFirst()
    )
    racetrack_code = scrapy.Field(
        output_processor=TakeFirst()
    )
    racetype = scrapy.Field(
        input_processor=MapCompose(handle_racetype),
        output_processor=TakeFirst()
    )
    driver = scrapy.Field(
        input_processor=MapCompose(handle_name),
        output_processor=TakeFirst()
    )
    racenumber = scrapy.Field(
        output_processor=TakeFirst()
    )
    postposition = scrapy.Field(
        output_processor=TakeFirst()
    )
    startnumber = scrapy.Field(
        output_processor=TakeFirst()
    )
    distance = scrapy.Field(
        input_processor=MapCompose(int),
        output_processor=TakeFirst()
    )
    monte = scrapy.Field(
        output_processor=TakeFirst()
    )
    finish = scrapy.Field(
        output_processor=TakeFirst()
    )
    racetime = scrapy.Field(
        input_processor=MapCompose(handle_racetime),
        output_processor=TakeFirst()
    )
    startmethod = scrapy.Field(
        output_processor=TakeFirst()
    )
    gallop = scrapy.Field(
        output_processor=TakeFirst()
    )
    purse = scrapy.Field(
        output_processor=TakeFirst()
    )
    ev_odds = scrapy.Field(
        output_processor=TakeFirst()
    )
    disqualified = scrapy.Field(
        input_processor=MapCompose(is_disqualified),
        output_processor=TakeFirst()
    )
    disqstring = scrapy.Field(
        input_processor=MapCompose(handle_disqualification),
        output_processor=TakeFirst()
    )
    started = scrapy.Field(
        input_processor=MapCompose(did_start),
        output_processor=TakeFirst()
    )
