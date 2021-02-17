from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from scrapy.selector import Selector
from germany.items import HorseItem
from w3lib.html import remove_tags

from scrapy_splash import SplashRequest

import json
import os

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/germany'
BASE_URL = 'https://www.hvtonline.de'


def handle_cell(cell):
    if not cell.attrib.get('data-traberid'):
        return None

    horse = ItemLoader(item=HorseItem(), selector=cell)

    horse.add_xpath('link', './@data-traberid')
    horse.add_xpath('name', '.')
    horse.add_xpath('country', '.')

    if cell.attrib['class'].startswith('vater'):
        horse.add_value('sex', 'horse')
    else:
        horse.add_value('sex', 'mare')

    return horse


def add_parents(horse, sire, dam):
    if horse is not None:
        if sire is not None:
            horse.add_value('sire', sire.load_item())

        if dam is not None:
            horse.add_value('dam', dam.load_item())


class HorseCollector(Spider):
    """
    Collects horses from 'https://www.hvtonline.de'.
    Takes a start_id to kick it off, it collects information about the horse,
    its pedigree, offspring and starts. If it is a mare and it has offspring,
    all these will also be collected.
    """
    name = 'horsecollector'
    allowed_domains = ['hvtonline.de']


    def __init__(self, start_id, *args, **kwargs):
        super(HorseCollector, self).__init__(*args, **kwargs)
        self.id = start_id
        self.lua_source = """
                          treat = require('treat')
                          function main(splash, args)
                            splash.response_body_enabled = true
                            local htmlList = {}
                            splash:go(args.url)
                            assert(splash:wait(2))
                            splash:on_response(
                                function(response)
                                    htmlList[#htmlList + 1] = treat.as_string(response.body)
                                end
                            )
                            splash:go{
                                args.url .. "/ajax/trabersuchefirst.php",
                                http_method="POST",
                                body="horseid=" .. args.id .. "&p=1"
                            }
                            assert(splash:wait(5))

                            tabs = {"1", "2", "3", "4"}
                            for _, tabNo in ipairs(tabs) do
                                splash:go{
                                    args.url .. "/ajax/trabersuchechange.php",
                                    http_method="POST",
                                    body="horseid=" .. args.id .. "&tab=" ..tabNo
                                }
                                assert(splash:wait(5))
                            end
                            return treat.as_array(htmlList)
                          end
                          """


    def start_requests(self):
        yield SplashRequest(
                url=BASE_URL,
                callback=self.parse,
                endpoint='execute',
                args={
                    'wait': 5,
                    'lua_source': self.lua_source,
                    'id': self.id
                }
            )


    def parse(self, response):
        for index, res in enumerate(response.data, 1):
            if index == 1:
                horse_json = json.loads(res)

                horse_html = Selector(text=horse_json['html'])

                horse = ItemLoader(item=HorseItem(), selector=horse_html)

                horse.add_xpath('link', '//span[contains(text(), "ID:")]')
                horse.add_xpath('ueln', '//span[contains(text(), "UELN:")]')
                horse.add_xpath('chip', '//span[contains(text(), "CHIP:")]')
                horse.add_xpath('name', '//td[text()="Name des Trabers:"]//following-sibling::td')
                horse.add_xpath('country', '//td[text()="Name des Trabers:"]//following-sibling::td')
                horse.add_xpath('sex', '//td[text()="Geschlecht:"]//following-sibling::td')
                horse.add_xpath('birthdate', '//td[text()="Geburtsdatum:"]//following-sibling::td')
                horse.add_xpath('breeder', '//td[text()="Züchter:"]//following-sibling::td')

                purse = horse_html.xpath('.//td[text()="Lebensgewinnsumme:"]//following-sibling::td').get()
                purse = int(remove_tags(purse).replace('.', '').replace('€', '').strip())

                mark = horse_html.xpath('.//td[text()="Rekord / Distanz / Datum:"]//following-sibling::td')
                mark = [remove_tags(x.get()) for x in mark]

                if mark[1] == '- / -':
                    mark.pop(1)

                if mark[0] != '- / -':
                    mark[0] = mark[0].replace(' /', 'a /')
                else:
                    mark.pop(0)

                if len(mark) != 0:
                    mark = ' - '.join(mark)
                else:
                    mark = None

                placings = horse_html.xpath('.//td[text()="Starts / Siege / Plätze:"]//following-sibling::td')
                placings = [int(x) if x.strip().isdigit() else 0 for x in remove_tags(placings.get()).split('/') ]

                if placings[0] != 0:
                    horse.add_value('start_summary', {
                        'year': 0,
                        'starts': placings[0],
                        'wins': placings[1],
                        'purse': purse,
                        'mark': mark
                    })

            elif index == 2:
                start_html = Selector(text=res)

                for row in start_html.xpath('//tbody/tr'):
                    columns_text = [remove_tags(x.get()) for x in row.xpath('./td')]

                    if len(columns_text) == 10:
                        start = {
                            'country': 'DE',
                            'racetrack': columns_text[1],
                            'racetype': 'race',
                            'racedate': '-'.join(reversed(columns_text[0].split('.'))),
                            'distance': int(columns_text[4].replace('.', '').replace(' m', '')),
                            'startmethod': 'mobile' if columns_text[5] == 'A' else 'standing',
                            'startnumber': int(columns_text[7]) if columns_text[7].isdigit() else None,
                            'ev_odds': float(columns_text[8].replace(',', '.')) if columns_text[8] != '-' else None,
                            'purse': int(columns_text[9].replace('.', '').replace(' €', '')) if columns_text[9] != '-' else None,
                        }

                        if '(' in columns_text[1]:
                            start['country'] = columns_text[1][
                                columns_text[1].find('(') + 1 : columns_text[1].find(')')
                            ]
                            start['racetrack'] = columns_text[1][ : columns_text[1].find('(')].strip()


                        if columns_text[6] in ['WQ', 'QU']:
                            start['racetype'] = 'qualifier'
                        else:
                            start['finish'] = int(columns_text[2].replace('.', ''))

                        if columns_text[3] != 'o.Z.':
                            start['racetime'] = int(columns_text[3][0]) * 60 + int(columns_text[3][2:4]) + int(columns_text[3][5]) / 10

                    elif len(columns_text) == 3:
                        start['driver'] = columns_text[1]

                        horse.add_value('starts', start)

            elif index == 3:
                ancestor_html = Selector(text=res)

                dams_offspring_list = []

                for offspring_table in ancestor_html.xpath('//table[@class="produkte"]'):
                    offspring_list = []

                    for offspring_row in offspring_table.xpath('.//tr')[ 1 : ]:
                        offspring = ItemLoader(item=HorseItem(), selector=offspring_row)

                        offspring.add_xpath('birthdate', './td[1]')
                        offspring.add_xpath('link', '../a/@data-traberid')

                        name_string = offspring_row.xpath('.//a/text()').get()

                        offspring.add_value('name', name_string)
                        offspring.add_value('sex', name_string[ name_string.find('(') + 1 : name_string.find(')')])

                        sire = ItemLoader(item=HorseItem())

                        sire.add_value('name', name_string[ name_string.find('v. ') + 3 : ])
                        sire.add_value('sex', 'horse')

                        offspring.add_value('sire', sire.load_item())

                        offspring_list.append(offspring.load_item())

                    dams_offspring_list.append(offspring_list)

            elif index == 4:
                pedigree_html = Selector(text=res)

                ancestors = [handle_cell(x) for x in pedigree_html.xpath('//div[@class="generations"]/a')]

                if len(dams_offspring_list[0]) != 0:
                    ancestors[61].add_value('offspring', dams_offspring_list[0])

                if len(dams_offspring_list[1]) != 0:
                    ancestors[59].add_value('offspring', dams_offspring_list[1])

                if len(dams_offspring_list[2]) != 0:
                    ancestors[55].add_value('offspring', dams_offspring_list[2])

                add_parents(ancestors[32], ancestors[0], ancestors[1])
                add_parents(ancestors[33], ancestors[2], ancestors[3])
                add_parents(ancestors[34], ancestors[4], ancestors[5])
                add_parents(ancestors[35], ancestors[6], ancestors[7])
                add_parents(ancestors[36], ancestors[8], ancestors[9])
                add_parents(ancestors[37], ancestors[10], ancestors[11])
                add_parents(ancestors[38], ancestors[12], ancestors[13])
                add_parents(ancestors[39], ancestors[14], ancestors[15])
                add_parents(ancestors[40], ancestors[16], ancestors[17])
                add_parents(ancestors[41], ancestors[18], ancestors[19])
                add_parents(ancestors[42], ancestors[20], ancestors[21])
                add_parents(ancestors[43], ancestors[22], ancestors[23])
                add_parents(ancestors[44], ancestors[24], ancestors[25])
                add_parents(ancestors[45], ancestors[26], ancestors[27])
                add_parents(ancestors[46], ancestors[28], ancestors[29])
                add_parents(ancestors[47], ancestors[30], ancestors[31])

                add_parents(ancestors[48], ancestors[32], ancestors[33])
                add_parents(ancestors[49], ancestors[34], ancestors[35])
                add_parents(ancestors[50], ancestors[36], ancestors[37])
                add_parents(ancestors[51], ancestors[38], ancestors[39])
                add_parents(ancestors[52], ancestors[40], ancestors[41])
                add_parents(ancestors[53], ancestors[42], ancestors[43])
                add_parents(ancestors[54], ancestors[44], ancestors[45])
                add_parents(ancestors[55], ancestors[46], ancestors[47])

                add_parents(ancestors[56], ancestors[48], ancestors[49])
                add_parents(ancestors[57], ancestors[50], ancestors[51])
                add_parents(ancestors[58], ancestors[52], ancestors[53])
                add_parents(ancestors[59], ancestors[54], ancestors[55])

                add_parents(ancestors[60], ancestors[56], ancestors[57])
                add_parents(ancestors[61], ancestors[58], ancestors[59])

                add_parents(horse, ancestors[60], ancestors[61])

            elif index == 5:
                offspring_html = Selector(text=res)

                for offspring_row in offspring_html.xpath('//table[@class="gestuetbuch"]//tr'):
                    if remove_tags(offspring_row.get()).strip() == 'Keine Daten vorhanden!':
                        break

                    if offspring_row.xpath('.//td[1]/text()').get().strip() != '…':
                        birthdate = offspring_row.xpath('.//td[1]/text()').get()

                    offspring = ItemLoader(item=HorseItem(), selector=offspring_row)

                    offspring.add_xpath('name', './/td[2]')
                    offspring.add_xpath('country', './/td[2]')
                    offspring.add_xpath('link', './/td[2]/a/@data-traberid')
                    offspring.add_value('birthdate', birthdate)
                    offspring.add_xpath('sex', './/td[4]')

                    offspring.add_value('start_summary', {
                        'year': 0,
                        'mark': offspring_row.xpath('.//td[5]/text()').get(),
                        'purse': offspring_row.xpath('.//td[6]/text()').get(),
                    })

                    if (horse.get_output_value('sex') == 'mare' and
                        not os.path.exists(os.path.join(
                            JSON_DIRECTORY, 'horses', offspring.get_output_value('link') + '.json'))):

                        yield SplashRequest(
                            url=BASE_URL,
                            callback=self.parse,
                            endpoint='execute',
                            args={
                                'wait': 5,
                                'lua_source': self.lua_source,
                                'id': offspring.get_output_value('link')
                            }
                        )

                    horse.add_value('offspring', offspring.load_item())

        yield horse.load_item()
