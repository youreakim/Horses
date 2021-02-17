from scrapy.spiders import Spider
from scrapy.http import JsonRequest
from scrapy.loader import ItemLoader
from scrapy.selector import Selector
from scrapy_splash import SplashRequest
from base64 import b64decode

from belgium.items import HorseItem, handle_racetime, handle_startmethod

import json
import os

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/belgium'
BASE_URL = 'https://www.trotting.be/horses/Overview/?horseId={}'


def create_horse(horse_json, offspring_list=None):
    if horse_json['HorseId'] is None:
        return None

    horse = ItemLoader(item=HorseItem())

    horse.add_value('name', horse_json['Name'])
    horse.add_value('link', str(horse_json['HorseId']))
    horse.add_value('country', horse_json['NationalityOfBirthText'])
    horse.add_value('registration', horse_json['OldHorseId'])
    horse.add_value('sex', horse_json['GenderText'])

    if offspring_list is not None:
        for offspring_json in offspring_list:
            offspring = create_horse(offspring_json)

            horse.add_value('offspring', offspring.load_item())

    return horse


def add_parents(horse, sire, dam):
    if horse is not None:
        if sire is not None:
            horse.add_value('sire', sire.load_item())

        if dam is not None:
            horse.add_value('dam', dam.load_item())

    return horse


class HorseCollector(Spider):
    """
    Collects horses from 'https://www.trotting.be/'
    Takes an id of a horse and collects pedigree, offspring and starts. If the horse
    is a mare her offspring will also be collected.
    Due to the fact that the horses UELN can only be found in the html files while
    the ids of the horses only is found in the json-files that are requested, I
    saved everything to a HAR file, and extracted information from that.
    """
    name = 'horsecollector'
    allowed_domains = ['trotting.be']


    def __init__(self, start_id, *args, **kwargs):
        super(HorseCollector, self).__init__(*args, **kwargs)
        self.start_id = start_id
        self.lua_source = """
                          function main(splash, args)
                            splash.response_body_enabled = true
                            splash.private_mode_enabled = false
                            assert(splash:go(args.url))
                            assert(splash:wait(3))
                            local nextTab = splash:select('ul.nav-tabs li.active+li')
                            while nextTab do
                                nextTab:mouse_click()
                                assert(splash:wait(3))
                                nextTab = splash:select('ul.nav-tabs li.active+li')
                            end
                            return splash:har()
                          end
                          """


    def start_requests(self):
        yield SplashRequest(
                    url=BASE_URL.format(self.start_id),
                    callback=self.parse,
                    endpoint='execute',
                    args={'lua_source': self.lua_source}
        )


    def parse(self, response):
        horse = ItemLoader(item=HorseItem())

        for entry in response.data['log']['entries']:
            if '/Overview/' in entry['response']['url']:
                horse.selector = Selector(text=b64decode(entry['response']['content']['text']))

                horse.add_xpath('name', '//span[@class="h4"]')
                horse.add_xpath('sex', '//span[@class="h4"]//following-sibling::text()')
                horse.add_xpath('link', '//label[text()="ID:"]//parent::div//parent::div//span')
                horse.add_xpath('country',
                        '//label[text()="Nationalité:"]//parent::div//following-sibling::div/span/span[1]')
                horse.add_xpath('birthdate',
                        '//label[text()="Date de naissance:"]//parent::div//parent::div//span')
                horse.add_xpath('registration', '//label[text()="Ancien id:"]//parent::div//parent::div//span')
                horse.add_xpath('birthdate', '//label[text()="Numéro UELN:"]//parent::div//parent::div//span')

            elif '/Overview?' in entry['response']['url']:
                horse_json = json.loads(b64decode(entry['response']['content']['text']))

                for breeder_json in horse_json['Breeders']:
                    horse.add_value('breeder', breeder_json['Participant']['Name'])

            elif '/ProductionOverview?' in entry['response']['url']:
                horse_json = json.loads(b64decode(entry['response']['content']['text']))

                for offspring_json in horse_json['BirthDeclarations']:
                    offspring = ItemLoader(item=HorseItem())

                    offspring.add_value('link', str(offspring_json['FoalHorse']['HorseId']))
                    offspring.add_value('name', offspring_json['FoalHorse']['Name'])
                    offspring.add_value('country', offspring_json['FoalHorse']['NationalityOfBirthText'])
                    offspring.add_value('registration', offspring_json['FoalHorse']['OldHorseId'])
                    offspring.add_value('sex', offspring_json['FoalHorse']['GenderText'])
                    offspring.add_value('birthdate', offspring_json['FoalHorse']['DateOfBirth'])
                    offspring.add_value('breed', offspring_json['FoalHorse']['TypeText'])

                    parent = ItemLoader(item=HorseItem())

                    parent.add_value('link', str(offspring_json['PartnerHorse']['HorseId']))
                    parent.add_value('name', offspring_json['PartnerHorse']['Name'])
                    parent.add_value('country', offspring_json['PartnerHorse']['NationalityOfBirthText'])
                    parent.add_value('registration', offspring_json['PartnerHorse']['OldHorseId'])
                    parent.add_value('sex', offspring_json['PartnerHorse']['GenderText'])
                    parent.add_value('breed', offspring_json['PartnerHorse']['TypeText'])

                    offspring.add_value('dam' if parent.get_output_value('sex') == 'mare' else 'sire',
                        parent.load_item())

                    filename = f'{offspring.get_output_value("link")}.json'

                    if (horse.get_output_value('sex') == 'mare' and
                        not os.path.exists(os.path.join(JSON_DIRECTORY, 'horses', filename))):
                        yield SplashRequest(
                                    url=BASE_URL.format(offspring.get_output_value('link')),
                                    callback=self.parse,
                                    endpoint='execute',
                                    args={'lua_source': self.lua_source})

                    horse.add_value('offspring', offspring.load_item())

            elif '/ResultOverview?' in entry['response']['url']:
                horse_json = json.loads(b64decode(entry['response']['content']['text']))

                for result_json in horse_json['Results']:
                    horse.add_value('starts', {
                        'link': result_json['Race']['RaceId'],
                        'status': result_json['Race']['PublicStateText'],
                        'race_name': result_json['Race']['Name'],
                        'racetrack': result_json['Race']['Track']['Name'],
                        'race_country': result_json['Race']['Track']['CountryText'],
                        'racedate': result_json['Race']['DepartureDateTime'],
                        'racenumber': result_json['Race']['RaceNumber'],
                        'race_distance': result_json['Race']['Distance'],
                        'monte': result_json['Race']['DisciplineText'],
                        'startmethod': handle_startmethod(result_json['Race']['StartTypeText']),
                        'racetype': result_json['Race']['RaceCategory']['Name'],
                        'distance': result_json['Participation']['Distance'],
                        'driver': result_json['Participation']['DriverName'],
                        'trainer': result_json['Participation']['TrainerName'],
                        'finish': result_json['Participation']['Place'],
                        'racetime': handle_racetime(result_json['Participation']['FormattedResultTime1000Txt']),
                        'purse': result_json['Participation']['TotalWinsum']
                    })

            elif '/PedigreeTree?' in entry['response']['url']:
                horse_json = json.loads(b64decode(entry['response']['content']['text']))

                add_parents(horse,
                    add_parents(create_horse(horse_json['Father']),
                        add_parents(create_horse(horse_json['GrandFather1']),
                            add_parents(create_horse(horse_json['GreatGrandFather1']),
                                create_horse(horse_json['GreatGreatGrandFather1']),
                                create_horse(horse_json['GreatGreatGrandMother1'])
                            ),
                            add_parents(create_horse(horse_json['GreatGrandMother1']),
                                create_horse(horse_json['GreatGreatGrandFather2']),
                                create_horse(horse_json['GreatGreatGrandMother2'])
                            )
                        ),
                        add_parents(create_horse(horse_json['GrandMother1']),
                            add_parents(create_horse(horse_json['GreatGrandFather2']),
                                create_horse(horse_json['GreatGreatGrandFather3']),
                                create_horse(horse_json['GreatGreatGrandMother3'])
                            ),
                            add_parents(create_horse(horse_json['GreatGrandMother2']),
                                create_horse(horse_json['GreatGreatGrandFather4']),
                                create_horse(horse_json['GreatGreatGrandMother4'])
                            )
                        )
                    ),
                    add_parents(create_horse(horse_json['Mother'],
                                        horse_json['MotherDescendants']),
                        add_parents(create_horse(horse_json['GrandFather2']),
                            add_parents(create_horse(horse_json['GreatGrandFather3']),
                                create_horse(horse_json['GreatGreatGrandFather5']),
                                create_horse(horse_json['GreatGreatGrandMother5'])
                            ),
                            add_parents(create_horse(horse_json['GreatGrandMother3']),
                                create_horse(horse_json['GreatGreatGrandFather6']),
                                create_horse(horse_json['GreatGreatGrandMother6'])
                            )
                        ),
                        add_parents(create_horse(horse_json['GrandMother2'],
                                        horse_json['GrandMotherDescendants']),
                            add_parents(create_horse(horse_json['GreatGrandFather4']),
                                create_horse(horse_json['GreatGreatGrandFather7']),
                                create_horse(horse_json['GreatGreatGrandMother7'])
                            ),
                            add_parents(create_horse(horse_json['GreatGrandMother4'],
                                        horse_json['GreatGrandMotherDescendants']),
                                create_horse(horse_json['GreatGreatGrandFather8']),
                                create_horse(horse_json['GreatGreatGrandMother8'],
                                        horse_json['GreatGreatGrandMotherDescendants'])
                            )
                        )
                    )
                )

        yield horse.load_item()
