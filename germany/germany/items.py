import scrapy
from w3lib.html import remove_tags

from itemloaders.processors import MapCompose, TakeFirst, Join


# RacedayItem
def convert_to_string(date):
    return date.strftime('%Y-%m-%d')


def handle_racedate(date_string):
    if '/' in date_string:
        date_string = date_string.split('/')[-2]

        return '-'.join([date_string[ : 4 ], date_string[ 4 : 6 ], date_string[ 6 : ]])


def find_racetrack_code(url):
    return url.split('/')[-4]


def shorten_raceday_link(url):
    return '/'.join(url.split('/')[ -4 : -1 ])


def handle_racetrack(racetrack):
    if ' › ' in racetrack:
        racetrack = racetrack[ : racetrack.find(' › ')]

    return racetrack


# RaceItem
def shorten_race_link(url):
    return '/'.join(url.split('/')[ -4 : ])


def get_racetype(num_string):
    return 'qualifier' if 'q' in num_string.lower() or num_string.lower() in ['p', 'a'] else 'race'


def get_racenumber(num_string):
    if num_string.isdigit():
        return int(num_string)


def handle_racepurse(purse_string):
    if purse_string.isdigit():
        return purse_string

    if '€' in purse_string:
        purse_string = purse_string[ : purse_string.find('€')]

    if ':' in purse_string:
        purse_string = purse_string[ purse_string.find(':') + 1 : ]

    return purse_string.replace('.', '')


def get_startmethod(dist_string):
    return 'mobile' if dist_string[-1] == 'A' else 'standing'


def is_disqualified(time_string):
    return 'dis' in time_string


# RaceStarterItem
def handle_odds(number):
    number = number.replace(',', '.')

    return float(number) if number.replace('.', '').isnumeric() else 0


def handle_show_odds(number):
    return int(number) / 10 if number.strip().isnumeric() else 0


def handle_finish(finish):
    return int(finish[ : -1 ]) if finish[ : -1 ].isnumeric() else 0


def handle_distance(distance):
    if isinstance(distance, int):
        return distance

    if ':' in distance:
        distance = distance[ distance.find(':') + 1 : ]

    if '/' in distance:
        distance = distance[ : distance.find('/') ]

    if 'm' in distance:
        distance = distance.replace('m', '')

    return int(distance.replace('.', '').strip())


def handle_racetime(racetime):
    if ',' in racetime:
        return float(racetime.replace(',', '.'))


# HorseItem
def handle_name(name_string):
    if '(' in name_string:
        return name_string[ : name_string.find('(') ]

    elif '[' in name_string:
        return name_string[ : name_string.find('[') ]

    return name_string


def handle_country(name_string):
    if '(' in name_string:
        country_string =  name_string[ name_string.find('(') + 1 : name_string.find(')') ]

    elif '[' in name_string:
        country_string = name_string[ name_string.find('[') + 1 : name_string.find(']') ]

    else:
        return 'DE'

    if len(country_string) == 2:
        return country_string
    else:
        return 'DE'


def handle_link(link_string):
    if ':' in link_string:
        link_string = link_string[ link_string.find(':') + 1 : ]

    return link_string


def handle_sex(gender_string):
    if gender_string in ['gelding', 'horse', 'mare']:
        return gender_string

    return {
        'S': 'mare',
        'H': 'horse',
        'W': 'gelding',
        'Stute': 'mare',
        'Hengst': 'horse',
        'Wallach': 'gelding'
    }[gender_string]


def remove_title(string):
    return string[ string.find(':') + 1 : ].strip()


def handle_birthdate(date_string):
    if '.' in date_string:
        return '-'.join(reversed(date_string.split('.')))

    if len(date_string) == 4 and date_string.isdigit():
        return f'{date_string}-01-01'

    return None


class RacedayItem(scrapy.Item):
    date = scrapy.Field(
        input_processor = MapCompose(handle_racedate),
        output_processor = TakeFirst()
    )
    racetrack = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_racetrack),
        output_processor = TakeFirst()
    )
    racetrack_code = scrapy.Field(
        input_processor = MapCompose(find_racetrack_code),
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(shorten_raceday_link),
        output_processor = TakeFirst()
    )
    races = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    collection_date = scrapy.Field(
        input_processor = MapCompose(convert_to_string),
        output_processor = TakeFirst()
    )
    status = scrapy.Field(
        output_processor = TakeFirst()
    )


class RaceItem(scrapy.Item):
    conditions = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = Join(separator='\n')
    )
    distance = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_distance),
        output_processor = TakeFirst()
    )
    purse = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_racepurse, str.strip, int),
        output_processor = TakeFirst()
    )
    racenumber = scrapy.Field(
        input_processor = MapCompose(remove_tags, get_racenumber),
        output_processor = TakeFirst()
    )
    monte = scrapy.Field(
        output_processor = TakeFirst()
    )
    startmethod = scrapy.Field(
        input_processor = MapCompose(remove_tags, get_startmethod),
        output_processor = TakeFirst()
    )
    racetype = scrapy.Field(
        input_processor = MapCompose(remove_tags, get_racetype),
        output_processor = TakeFirst()
    )
    status = scrapy.Field(
        output_processor = TakeFirst()
    )
    link = scrapy.Field(
        input_processor = MapCompose(shorten_race_link),
        output_processor = TakeFirst()
    )
    starters = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    racename = scrapy.Field(
        input_processor = MapCompose(remove_tags),
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
        input_processor = MapCompose(remove_tags, int),
        output_processor = TakeFirst()
    )
    distance = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_distance),
        output_processor = TakeFirst()
    )
    racetime = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_racetime),
        output_processor = TakeFirst()
    )
    driver = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
    trainer = scrapy.Field(
        input_processor = MapCompose(remove_tags),
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
        input_processor = MapCompose(remove_tags, handle_odds),
        output_processor = TakeFirst()
    )
    show_odds = scrapy.Field(
        input_processor = MapCompose(handle_show_odds),
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
        input_processor = MapCompose(remove_tags, is_disqualified),
        output_processor = TakeFirst()
    )
    disqstring = scrapy.Field(
        input_processor = MapCompose(remove_tags),
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
        input_processor = MapCompose(remove_tags, handle_link, str.strip),
        output_processor = TakeFirst()
    )
    country = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_country, str.upper, str.strip),
        output_processor = TakeFirst()
    )
    birthdate = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_birthdate),
        output_processor = TakeFirst()
    )
    sex = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_sex),
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
    ueln = scrapy.Field(
        input_processor = MapCompose(remove_tags, remove_title),
        output_processor = TakeFirst()
    )
    chip = scrapy.Field(
        input_processor = MapCompose(remove_tags, remove_title),
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
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
