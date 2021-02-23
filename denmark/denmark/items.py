import scrapy
from itemloaders.processors import MapCompose, TakeFirst, Join
from w3lib.html import remove_tags


# RacedayItem
def handle_raceday_link(link):
    link = link[ link.find('tevdagId=') + len('tevdagId=') : ]

    if '&' in link:
        link = link[ : link.find('&') ]

    if link.isdigit():
        return link


# RaceItem
def handle_race_link(link):
    if 'loppId' in link:
        link = link[ link.find('&loppId=') + 8 : ]

    if '&' in link:
        link = link[ : link.find('&') ]

    if link.isdigit():
        return link


def handle_racetype(tab_string):
    return 'race' if tab_string.strip().isdigit() else 'qualifier'


def get_racenumber(num_string):
    return num_string[ num_string.find('Løb ') + 4 : num_string.find('.')]


def calculate_purse(purse_string):
    purse_string = purse_string[ purse_string.find(':') + 1 : purse_string.find(' (') ]

    return sum(int(x.replace('.', '')) for x in purse_string.split('-'))


def filter_racename(racename):
    if ' kr.' not in racename:
        return racename


# RaceStarterItem
def handle_odds(odds):
    if ',,' in odds:
        odds = odds.replace(',,', ',')

    if odds == '' or '-' in odds:
        return 0
    elif '(' in odds or ',' not in odds:
        return int(''.join([x for x in odds if x.isnumeric()]))

    return float(odds.replace(',', '.'))


def remove_comma(odds):
    if ',' in odds:
        return ''.join([x for x in odds[ : -1 ] if x.isnumeric()])

    return odds


def is_approved(approved):
    return 'gk' in approved


def is_disqualified(place_string):
    return 'd' in place_string


def place(place_string):
    return int(place_string) if place_string.isdigit() else 0


def did_finish(time_string):
    return 'opg' not in time_string


def made_a_break(time_string):
    return 'g' in time_string.replace('opg', '')


def handle_distance(dist_string):
    if len(dist_string) >= 3 and dist_string.isdigit():
        return dist_string

    if '/' in dist_string:
        return dist_string.split('/')[1]


def handle_post(post_string):
    if post_string.isdigit() and len(post_string) <= 2:
        return post_string

    if '/' in post_string:
        return post_string.split('/')[0]


def handle_racetime(time_string):
    if ',' in time_string:
        time_string = time_string.replace(',', '.')

        if len(time_string) >= 4 and time_string.index('.') == 2:
            return time_string[ : 4]


def reason(time_string):
    time_string = time_string.replace('a', '').replace('opg', '').replace('g', '')

    if time_string.strip() != '':
        return time_string


# HorseItem
def handle_name(name):
    if '(' in name:
        name = name[ : name.find('(')]

    return name.replace('*', '')


def handle_country(country):
    if '(' in country:
        return country[ country.find('(') + 1 : country.find(')') ]

    return 'DK'


def handle_gender(gender):
    if gender in ['gelding', 'horse', 'mare']:
        return gender

    return {
        'hingst': 'horse',
        'hoppe': 'mare',
        'vallak': 'gelding'
    }[ gender ]


def handle_horse_link(link):
    link = link.split('/')

    if link[0] in ['.', '..']:
        return link[1]

    return link[ link.index('visa') + 1 ]


def filter_ueln(ueln):
    if len(ueln) == 15:
        return ueln


def handle_breed(breed):
    if 'varmblodig' in breed:
        return 'standardbred'


def handle_date(date_string):
    if '(' in date_string:
        date_string = date_string[ : date_string.find('(') ]

    if '-' not in date_string:
        if date_string.isdigit():
            date_string += '-01-01'
        else:
            return None

    return date_string


class RacedayItem(scrapy.Item):
    date = scrapy.Field(
        output_processor = TakeFirst()
    )
    racetrack = scrapy.Field(
        output_processor = TakeFirst()
    )
    racetrack_code  = scrapy.Field(
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(handle_raceday_link),
        output_processor = TakeFirst()
    )
    races = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    collection_date = scrapy.Field(
        input_processor = MapCompose(),
        output_processor = TakeFirst()
    )
    status = scrapy.Field(
        output_processor = TakeFirst()
    )


class RaceItem(scrapy.Item):
    conditions = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = Join(separator='\n')
    )
    distance = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        input_processor = MapCompose(remove_tags, calculate_purse),
        output_processor = TakeFirst()
    )
    racenumber = scrapy.Field(
        input_processor = MapCompose(remove_tags, get_racenumber, int),
        output_processor = TakeFirst()
    )
    monte = scrapy.Field(
        output_processor = TakeFirst()
    )
    startmethod = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
    racetype = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_racetype),
        output_processor = TakeFirst()
    )
    status = scrapy.Field(
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(handle_race_link),
        output_processor = TakeFirst()
    )
    starters = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    racename = scrapy.Field(
        input_processor = MapCompose(remove_tags, filter_racename),
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
        input_processor = MapCompose(remove_tags, place),
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
        input_processor = MapCompose(remove_tags, handle_distance, int),
        output_processor = TakeFirst()
    )
    racetime = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_racetime, float),
        output_processor = TakeFirst()
    )
    driver = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        output_processor = TakeFirst()
    )
    odds = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_odds),
        output_processor = TakeFirst()
    )
    ev_odds = scrapy.Field(
        input_processor = MapCompose(remove_tags, remove_comma, handle_odds),
        output_processor = TakeFirst()
    )
    show_odds = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_odds),
        output_processor = TakeFirst()
    )
    gallop = scrapy.Field(
        input_processor = MapCompose(remove_tags, made_a_break),
        output_processor = TakeFirst()
    )
    finished = scrapy.Field(
        input_processor = MapCompose(remove_tags, did_finish),
        output_processor = TakeFirst()
    )
    approved = scrapy.Field(
        input_processor = MapCompose(remove_tags, is_approved),
        output_processor = TakeFirst()
    )
    started = scrapy.Field(
        output_processor = TakeFirst()
    )
    disqualified = scrapy.Field(
        input_processor = MapCompose(remove_tags, is_disqualified),
        output_processor = TakeFirst()
    )
    disqstring = scrapy.Field(
        input_processor = MapCompose(remove_tags, reason),
        output_processor = TakeFirst()
    )
    postposition = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_post, int),
        output_processor = TakeFirst()
    )
    trainer = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
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
        input_processor = MapCompose(remove_tags, handle_date),
        output_processor = TakeFirst()
    )
    sex = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_gender),
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
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
    ueln = scrapy.Field(
        input_processor = MapCompose(remove_tags, filter_ueln),
        output_processor = TakeFirst()
    )
    chip = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
    breed = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_breed),
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
