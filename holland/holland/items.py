# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy
import re
from itemloaders.processors import MapCompose, TakeFirst, Join
from w3lib.html import remove_tags

def handle_date(date):
    if isinstance(date, str):
        date_split          = date.split('-')

        if len(date_split[-1]) == 2:
            date_split[-1]  = '20' + date_split[-1] if date_split[-1][-2] != 9 else '19' + date_split[-1]
            date            = '-'.join(reversed(date_split))

        return date

    return date.strftime('%Y-%m-%d')

def handle_driver(driver):
    return re.sub(r'\s{2,}', r' ', driver)

def handle_startnumber(number):
    return int(number)

def handle_number(number):
    return int(number)

def handle_racenumber(number):
    return int(number)

def handle_purse(purse):
    purse           = purse.replace('€ ', '').replace('.', '').replace(',00', '')
    return int(purse) if purse.isnumeric() else 0

def handle_racename(text):
    if '-' in text:
        return text[ text.find('-') + 1 : ].strip()
    return text

def handle_distance(distance):
    if '-' in distance:
        distance = distance.split('-')[1]

    return int(distance) if distance.strip().isnumeric() else 0

def handle_time(time):
    if time == '':
        return 0

    time_splits     = [int(x) for x in re.split('[\.\,]', time)]

    if len(time_splits) == 2:
        time_splits.append(0)

    return time_splits[0] * 60 + time_splits[1] + time_splits[2] / 10

def handle_odds(odds):
    if odds == '':
        return 0

    return float(odds.replace(',', '.'))

def handle_weight(weight):
    return float(weight[ : weight.find(' ') ].replace(',', '.'))

def handle_name(name_string):
    if '(' in name_string:
        return name_string[ : name_string.find('(')]

    return name_string

def handle_country(name_string):
    if len(name_string) < 3:
        return name_string

    if '(' in name_string:
        return name_string[ name_string.find('(') + 1 : name_string.find(')') ]

    if name_string[-1].isdigit():
        return ''.join(x for x in name_string if not x.isdigit())


def is_disqualified(place_string):
    return 'A' in place_string

def handle_finish(place_string):
    return int(place_string) if place_string.isdigit() else 0

def handle_startmethod(conditions):
    return 'mobile' if 'Autostart' in conditions else 'standing'

def handle_gait(conditions):
    return 'trot' if 'Drafsport' in conditions else 'gallop'

def handle_sex(sex):
    if sex in ['horse', 'gelding', 'mare']:
        return sex

    if '(' in sex:
        sex = sex[ sex.find('(') + 1 : sex.find(')') ]

    return {
        'Ruin': 'gelding',
        'Merrie': 'mare',
        'Hengst': 'horse',
        'R': 'gelding',
        'M': 'mare',
        'H': 'horse'
    }[sex]


class RacedayItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    date            = scrapy.Field(
        input_processor = MapCompose(handle_date),
        output_processor = TakeFirst()
    )
    racetrack       = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
    racetrack_code  = scrapy.Field(
        output_processor = TakeFirst()
    )
    link            = scrapy.Field(
        output_processor = TakeFirst()
    )
    races           = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    collection_date = scrapy.Field(
        input_processor = MapCompose(handle_date),
        output_processor = TakeFirst()
    )
    status          = scrapy.Field(
        output_processor = TakeFirst()
    )

class RaceItem(scrapy.Item):
    gait            = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_gait),
        output_processor = TakeFirst()
    )
    conditions      = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = Join(separator = '\n')
    )#
    distance        = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_distance),
        output_processor = TakeFirst()
    )#
    purse           = scrapy.Field(
        input_processor = MapCompose(handle_purse),
        output_processor = TakeFirst()
    )#
    racenumber      = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_racenumber),
        output_processor = TakeFirst()
    )#
    monte           = scrapy.Field(
        #input_processor = MapCompose(handle_monte),
        output_processor = TakeFirst()
    )#
    startmethod     = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_startmethod),
        output_processor = TakeFirst()
    )#
    racetype        = scrapy.Field(#
        output_processor = TakeFirst()
    )
    status          = scrapy.Field(
        output_processor = TakeFirst()
    )#
    link            = scrapy.Field(#
        output_processor = TakeFirst()
    )
    starters        = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    racename        = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )

# class RaceStarterItem(scrapy.Item):
#     horse           = scrapy.Field(#
#         input_processor = MapCompose(dict),
#         output_processor = TakeFirst()
#     )
#     finish          = scrapy.Field(
#         output_processor = TakeFirst()
#     )#
#     order           = scrapy.Field(
#         output_processor = TakeFirst()
#     )#
#     startnumber     = scrapy.Field(
#         input_processor = MapCompose(handle_startnumber),
#         output_processor = TakeFirst()
#     )#
#     distance        = scrapy.Field(
#         input_processor = MapCompose(handle_distance),
#         output_processor = TakeFirst()
#     )#
#     racetime        = scrapy.Field(
#         #input_processor = MapCompose(handle_time),
#         output_processor = TakeFirst()
#     )#
#     driver          = scrapy.Field(
#         input_processor = MapCompose(str.strip, handle_driver),
#         output_processor = TakeFirst()
#     )#
#     purse           = scrapy.Field(
#         #input_processor = MapCompose(handle_purse),
#         output_processor = TakeFirst()
#     )#
#     odds            = scrapy.Field(
#         output_processor = TakeFirst()
#     )
#     ev_odds         = scrapy.Field(
#         output_processor = TakeFirst()
#     )#
#     show_odds       = scrapy.Field(
#         output_processor = TakeFirst()
#     )
#     gallop          = scrapy.Field(
#         output_processor = TakeFirst()
#     )#
#     dnf             = scrapy.Field(
#         output_processor = TakeFirst()
#     )
#     approved        = scrapy.Field(
#         output_processor = TakeFirst()
#     )
#     started         = scrapy.Field(
#         output_processor = TakeFirst()
#     )#
#     disqualified    = scrapy.Field(
#         output_processor = TakeFirst()
#     )
#     disqstring      = scrapy.Field(
#         output_processor = TakeFirst()
#     )#
#     postposition    = scrapy.Field(
#         output_processor = TakeFirst()
#     )#
#     trainer         = scrapy.Field(
#         output_processor = TakeFirst()
#     )#

class TrotRaceStarterItem(scrapy.Item):
    horse           = scrapy.Field(#
        input_processor = MapCompose(dict),
        output_processor = TakeFirst()
    )
    finish          = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_finish),
        output_processor = TakeFirst()
    )#
    order           = scrapy.Field(
        output_processor = TakeFirst()
    )#
    startnumber     = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_startnumber),
        output_processor = TakeFirst()
    )#
    distance        = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_distance),
        output_processor = TakeFirst()
    )#
    racetime        = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_time),
        output_processor = TakeFirst()
    )#
    driver          = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_driver),
        output_processor = TakeFirst()
    )#
    purse           = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_purse),
        output_processor = TakeFirst()
    )#
    odds            = scrapy.Field(
        output_processor = TakeFirst()
    )
    ev_odds         = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_odds),
        output_processor = TakeFirst()
    )#
    show_odds       = scrapy.Field(
        output_processor = TakeFirst()
    )
    gallop          = scrapy.Field(
        output_processor = TakeFirst()
    )#
    dnf             = scrapy.Field(
        output_processor = TakeFirst()
    )
    approved        = scrapy.Field(
        output_processor = TakeFirst()
    )
    started         = scrapy.Field(
        output_processor = TakeFirst()
    )#
    disqualified    = scrapy.Field(
        input_processor = MapCompose(remove_tags, is_disqualified),
        output_processor = TakeFirst()
    )
    disqstring      = scrapy.Field(
        input_processor = MapCompose(str.strip),
        output_processor = TakeFirst()
    )#
    postposition    = scrapy.Field(
        output_processor = TakeFirst()
    )#
    trainer         = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )#

class GallopRaceStarterItem(scrapy.Item):
    horse           = scrapy.Field(#
        #input_processor = MapCompose(dict),
        output_processor = TakeFirst()
    )
    finish          = scrapy.Field(
        input_processor = MapCompose(handle_number),
        output_processor = TakeFirst()
    )#
    order           = scrapy.Field(
        output_processor = TakeFirst()
    )#
    startnumber     = scrapy.Field(
        input_processor = MapCompose(handle_number),
        output_processor = TakeFirst()
    )#
    box             = scrapy.Field(
        input_processor = MapCompose(handle_number),
        output_processor = TakeFirst()
    )
    racetime        = scrapy.Field(
        input_processor = MapCompose(str.strip, handle_time),
        output_processor = TakeFirst()
    )#
    distanced       = scrapy.Field(
        input_processor = MapCompose(str.strip),
        output_processor = TakeFirst()
    )
    weight          = scrapy.Field(
        input_processor = MapCompose(handle_weight),
        output_processor = TakeFirst()
    )
    jockey          = scrapy.Field(
        input_processor = MapCompose(str.strip, handle_driver),
        output_processor = TakeFirst()
    )#
    purse           = scrapy.Field(
        input_processor = MapCompose(str.strip, handle_purse),
        output_processor = TakeFirst()
    )#
    odds            = scrapy.Field(
        output_processor = TakeFirst()
    )
    ev_odds         = scrapy.Field(
        output_processor = TakeFirst()
    )#
    show_odds       = scrapy.Field(
        input_processor = MapCompose(str.strip, handle_odds),
        output_processor = TakeFirst()
    )
    dnf             = scrapy.Field(
        output_processor = TakeFirst()
    )
    started         = scrapy.Field(
        output_processor = TakeFirst()
    )#
    disqualified    = scrapy.Field(
        output_processor = TakeFirst()
    )
    disqstring      = scrapy.Field(
        input_processor = MapCompose(str.strip),
        output_processor = TakeFirst()
    )#
    trainer         = scrapy.Field(
        output_processor = TakeFirst()
    )#

class HorseItem(scrapy.Item):
    name            = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_name, str.strip, str.upper),
        output_processor = TakeFirst()
    )#
    link            = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = TakeFirst()
    )#
    country         = scrapy.Field(
        input_processor = MapCompose(remove_tags, handle_country, str.strip),
        output_processor = TakeFirst()
    )
    birthdate       = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = TakeFirst()
    )
    sex             = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip, handle_sex),
        output_processor = TakeFirst()
    )
    sire            = scrapy.Field(
        output_processor = TakeFirst(),
        input_processor = MapCompose(dict)
    )
    dam             = scrapy.Field(
        input_processor = MapCompose(dict),
        output_processor = TakeFirst()
    )
    registration    = scrapy.Field(
        input_processor = MapCompose(remove_tags, str.strip),
        output_processor = TakeFirst()
    )
    breed            = scrapy.Field(
        output_processor = TakeFirst()
    )
    offspring       = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    start_summary   = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    starts          = scrapy.Field(
        input_processor = MapCompose(dict)
    )
    breeder         = scrapy.Field(
        input_processor = MapCompose(remove_tags),
        output_processor = TakeFirst()
    )
    collection_date = scrapy.Field(
        output_processor = TakeFirst()
    )
    collection_date = scrapy.Field(
        output_processor = TakeFirst()
    )
