from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from scrapy.selector import Selector
from w3lib.html import remove_tags

from scrapy_splash import SplashFormRequest, SplashRequest

from finland.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

import datetime
import re
import os


JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/finland/'
BASE_URL = 'http://heppa.hippos.fi/heppa/horse/FamilyInfo,$HorseLink.$DirectLink.sdirect?sp=l{}&sp=X'


def handle_date(date_string):
    if '.' in date_string:
        splits = [x if len(x) != 1 else '0' + x for x in date_string.split('.')]
        return '-'.join(reversed(splits))

    elif date_string:
        return date_string + '-01-01'


def handle_cell(cell):
    """
    Each cell of the pedigree can contain an ancestor
    If so there can also be a birthdate/birthyear, registration number and country
    """
    if not cell.xpath('./a'):
        return None

    horse = ItemLoader(item=HorseItem(), selector=cell)

    horse.add_xpath('name', './a')
    horse.add_xpath('link', './a/@href')
    horse.add_value('sex', 'mare' if cell.attrib['class'] == 'mother' else 'horse')

    cell_text = [x.strip() for x in cell.xpath('./text()').getall() if x.strip() != '']

    if ' ' in cell_text[0]:
        rcb_text = cell_text[0].split()

        horse.add_value('registration', rcb_text[0])

        if len(rcb_text) == 3:
            horse.add_value('country', rcb_text[1])
            horse.add_value('birthdate', rcb_text[2])
        elif len(rcb_text[1]) == 2:
            horse.add_value('country', rcb_text[1])
        elif rcb_text[1][0].isdigit():
            horse.add_value('birthdate', rcb_text[1])

    else:
        horse.add_value('registration', cell_text[0])

        cb_text = cell_text[1][ cell_text[1].find('\n') + 1 : ].strip().split()
        if len(cb_text) == 2:
            horse.add_value('country', cb_text[0])
            horse.add_value('birthdate', cb_text[1])
        elif cb_text[0].isdigit():
            horse.add_value('birthdate', cb_text[0])
        elif len(cb_text[0]) == 2:
            horse.add_value('country', cb_text[0])

    return horse


def add_parents(horse, sire, dam):
    if horse is not None:
        if sire is not None:
            horse.add_value('sire', sire.load_item())

        if dam is not None:
            horse.add_value('dam', dam.load_item())


def handle_racetime(time_string):
    if time_string is not None:
        splits = time_string.split('.')

        if len(splits) == 1:
            return 0

        return int(splits[0][-1]) * 60 + int(splits[1]) + int(splits[2][0]) / 10

    return 0


def handle_startmethod(str):
    return {
        'ryhmä': 'mobile',
        'linja': 'line',
        'tasoitus': 'standing',
        'rutiini': 'rutiini'
    }[str.lower()]


class HorsecollectorSpider(Spider):
    """
    Collects horses from 'https://www.hippos.fi/'
    Takes an id of a horse as starting point and gets the basic information and
    pedigree about that horse, if available it also gets any offspring and
    racing career. If the horse is a mare it will continue to collect these horses.
    The id of a horse can be found in its url, the underlined part in this example:
    heppa.hippos.fi/heppa/horse/FamilyInfo,$HorseLink.$DirectLink.sdirect?sp=l6949548875419747522&sp=X
                                                                              ===================
    """
    name = 'horsecollector'
    allowed_domains = ['hippos.fi']

    def __init__(self, start_id = '', *args, **kwargs):
        super(HorsecollectorSpider, self).__init__(*args, **kwargs)
        self.id = start_id
        self.lua_source = """
                            treat = require('treat')
                            function main(splash, args)
                                local whichTabs = {
                                    ['Hevosen perustiedot'] = true,
                                    ['Suku ja jälkeläiset'] = true,
                                    ['Ravikilpailuhistoria'] = true
                                }
                                assert(splash:go(args.url))
                                assert(splash:wait(4))
                                local htmlList = {}
                                local selectedTab = splash:select('span.selected_tab a'):text()
                                if whichTabs[selectedTab] then
                                    htmlList[#htmlList + 1] = splash:html()
                                    whichTabs[selectedTab] = false
                                end
                                for _, v in ipairs({'tab_1', 'tab_2', 'tab_3'}) do
                                    selectedTab = splash:select('span.' .. v .. ' a')
                                    if whichTabs[selectedTab:text()] then
                                        selectedTab:mouse_click()
                                        assert(splash:wait(4))
                                        htmlList[#htmlList + 1] = splash:html()
                                        whichTabs[selectedTab] = false
                                    end
                                end
                                return treat.as_array(htmlList)
                            end
                          """


    def start_requests(self):
        yield SplashRequest(
            url = BASE_URL.format(self.id),
            callback = self.parse,
            endpoint = 'execute',
            args = {
                'wait': 5,
                'lua_source': self.lua_source
            }
        )


    def parse(self, response):
        horse = ItemLoader(item=HorseItem())

        for html in response.data:
            horse_html = Selector(text=html)
            selected_tab = horse_html.xpath('//span[contains(@class," selected_tab")]/a/@href').get()

            if 'HorseBasic' in selected_tab:
                horse.selector = horse_html

                horse.add_value('link', response.url)
                horse.add_xpath('name', '//span[@id="horse_name"]')
                horse.add_xpath('sex', '//label[@for="gender"]//following-sibling::text()')
                horse.add_xpath('ueln', '//label[@for="ueln"]//following-sibling::text()')
                horse.add_xpath('chip', '//label[@for="chipNo"]//following-sibling::text()')
                horse.add_xpath('birthdate', '//label[@for="birthDate"]//following-sibling::text()')
                horse.add_xpath('country', '//label[@for="birthCountry"]//following-sibling::text()')
                horse.add_xpath('registration', '//label[@for="registerNo"]//following-sibling::text()')
                horse.add_xpath('breed',
                    '//div[@id="basic_content_wide"]//label[@for="species"]//following-sibling::text()')
                horse.add_xpath('breeder', '//label[text()="Kasvattaja"]//following-sibling::text()')

            elif 'FamilyInfo' in selected_tab:
                pedigree = [handle_cell(x) for x in horse_html.xpath('//table[@class="familytree"]//td')]

                # sires half of the pedigree
                add_parents(pedigree[2], pedigree[3], pedigree[4])
                add_parents(pedigree[5], pedigree[6], pedigree[7])
                add_parents(pedigree[9], pedigree[10], pedigree[11])
                add_parents(pedigree[12], pedigree[13], pedigree[14])

                add_parents(pedigree[1], pedigree[2], pedigree[5])
                add_parents(pedigree[8], pedigree[9], pedigree[12])

                add_parents(pedigree[0], pedigree[1], pedigree[8])

                # dams half of the pedigree
                add_parents(pedigree[17], pedigree[18], pedigree[19])
                add_parents(pedigree[20], pedigree[21], pedigree[22])
                add_parents(pedigree[24], pedigree[25], pedigree[26])
                add_parents(pedigree[27], pedigree[28], pedigree[29])

                add_parents(pedigree[16], pedigree[17], pedigree[20])
                add_parents(pedigree[23], pedigree[24], pedigree[27])

                add_parents(pedigree[15], pedigree[16], pedigree[23])

                add_parents(horse, pedigree[0], pedigree[15])

                for offspring_row in horse_html.xpath('//table[@class="sortable no_wrap_table"]/tbody/tr'):
                    offspring = ItemLoader(item=HorseItem(), selector=offspring_row)

                    offspring.add_xpath('name', './td[2]')
                    offspring.add_xpath('birthdate', './td[3]')
                    offspring.add_xpath('sex', './td[4]')
                    offspring.add_xpath('registration', './td[5]')
                    offspring.add_xpath('link', './a[1]/@href')

                    if len(offspring_row.xpath('.//a')) > 1:
                        parent = ItemLoader(item=HorseItem(), selector=offspring_row.xpath('.//a[2]'))

                        parent.add_xpath('name', '.')
                        parent.add_xpath('link', './@href')
                        parent.add_value('sex', 'horse' if horse.get_output_value('sex') == 'mare' else 'mare')

                        offspring.add_value('sire' if horse.get_output_value('sex') == 'mare' else 'dam', parent.load_item())

                    offspring.add_value('start_summary', {
                        'year': 0,
                        'starts': int(offspring_row.xpath('./td[7]/text()').get()),
                        'wins': int(offspring_row.xpath('./td[8]/text()').get()),
                        'place': int(offspring_row.xpath('./td[9]/text()').get()),
                        'show': int(offspring_row.xpath('./td[10]/text()').get()),
                        'purse': int(offspring_row.xpath('./td[11]/text()').get()),
                        'mark': ' '.join([offspring_row.xpath('./td[12]/text()').get(),
                            offspring_row.xpath('./td[13]/text()').get()]).strip()
                    })

                    horse.add_value('offspring', offspring.load_item())

                    if horse.get_output_value('sex') == 'mare':
                        yield SplashRequest(
                            url = BASE_URL.format(offspring.get_output_value('link')),
                            callback = self.parse,
                            endpoint = 'execute',
                            args = {
                                'wait': 5,
                                'lua_source': self.lua_source
                            }
                        )

            elif 'RacingHistory' in selected_tab:
                # career table
                for summary_row in horse_html.xpath(
                        '//h4[contains(text(),"startit")]//parent::div//tbody/tr'):
                    columns_text = [remove_tags(x.get()).replace('\xa0', '').strip()
                        for x in summary_row.xpath('./td')]

                    horse.add_value('start_summary', {
                        'year': int(columns_text[0]) if columns_text[0].isdigit() else 0,
                        'starts': int(columns_text[1]),
                        'wins': int(columns_text[2]),
                        'place': int(columns_text[3]),
                        'show': int(columns_text[4]),
                        'purse': int(columns_text[5].replace('\xa0', '')[:-4]),
                        'mark': ' '.join(columns_text[6:8]).strip()
                    })

                # table with all race starts
                for start_row in horse_html.xpath(
                        '//h4[text()="Startit"]//parent::div//tbody/tr'):
                    columns_text = [remove_tags(x.get()).replace('\xa0', '').strip()
                        for x in start_row.xpath('./td')]

                    start = {
                        'racetrack_code': columns_text[0],
                        'racedate': handle_date(columns_text[2]),
                        'startnumber': int(columns_text[3]),
                        'startmethod': handle_startmethod(columns_text[6])
                    }

                    # was the horse scratched
                    if columns_text[7] == 'P':
                        start['started'] = False
                    else:
                        start['started'] = True
                        start['monte'] = 'm' in columns_text[7]
                        start['postposition'] = int(columns_text[4]) if columns_text[4] != '' else 0
                        start['distance'] = int(columns_text[5])
                        start['racetime'] = handle_racetime(columns_text[7])
                        start['finish'] = int(columns_text[9]) if columns_text[9] != '' else 0
                        start['extra'] = columns_text[10]

                        if columns_text[11] != '':
                            start['ev_odds'] = float(columns_text[11].replace(',', '.')) * 10

                        start['purse'] = int(columns_text[12][:-4]) if columns_text[12] != '' else 0

                        # driver and trainer not always available for foreign stars
                        if columns_text[13] != '':
                            start['driver'] = columns_text[13]

                        if columns_text[14]:
                            start['trainer'] = columns_text[14]

                    # link is only available for starts made in Finland
                    if start_row.xpath('./td[3]/a/@href'):
                        start['link'] = start_row.xpath('./td[3]/a/@href').get()

                    horse.add_value('starts', start)

        yield horse.load_item()
