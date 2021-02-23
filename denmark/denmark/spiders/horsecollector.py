import scrapy
from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from scrapy.selector import Selector
from denmark.items import HorseItem
from w3lib.html import remove_tags

from scrapy_splash import SplashRequest

import os

BASE_URL = 'http://195.198.34.45/trav/hast/visa/{}'
JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/denmark'


def handle_cell(cell):
    if not cell.xpath('./a'):
        return None

    horse = ItemLoader(item=HorseItem(), selector=cell.xpath('./a'))

    horse.add_xpath('name', './span')
    horse.add_xpath('country', './span')
    horse.add_xpath('link', './@href')

    if cell.attrib.get('class', '') == 'plain_odd':
        horse.add_value('sex', 'mare')
    else:
        horse.add_value('sex', 'horse')

    return horse


def add_parents(horse, sire, dam):
    if horse is not None:
        if sire is not None:
            horse.add_value('sire', sire.load_item())

        if dam is not None:
            horse.add_value('dam', dam.load_item())


class HorsecollectorSpider(Spider):
    """
    Collects horses from DTCs site.
    Takes a start_id and collects information about pedigree, racing career and
    offspring. If the horse is a mare and has offspring, those are also collected.
    """
    name = 'horsecollector'
    allowed_domains = ['195.198.34.45']


    def __init__(self, start_id = '', *args, **kwargs):
        super(HorsecollectorSpider, self).__init__(*args, **kwargs)
        self.id = start_id

        self.lua_source = """
                          treat = require('treat')
                          function main(splash, args)
                            local whichTabs = {
                                ['Afstamning'] = true,
                                ['Væddeløbsresultater'] = true,
                                ['Afkom'] = true
                            }
                            local htmlList = {}
                            assert(splash:go(args.url))
                            assert(splash:wait(5))
                            local selectedTab = splash:select('div.tab-row li.selected a'):text()
                            if whichTabs[selectedTab] then
                                htmlList[#htmlList + 1] = splash:html()
                                whichTabs[selectedTab] = false
                            end
                            for _, v in ipairs({'tab0', 'tab1', 'tab2', 'tab3'}) do
                                selectedTab = splash:select('div.tab-row li.' .. v .. ' a')
                                if selectedTab and whichTabs[selectedTab:text()] then
                                    selectedTab:mouse_click()
                                    assert(splash:wait(5))
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
            args= {
                'wait': 5,
                'lua_source': self.lua_source
            }
        )


    def parse(self, response):
        collect_basic = True

        horse = ItemLoader(item=HorseItem())

        horse.add_value('link', response.url)

        for html in response.data:
            horse_html = Selector(text=html)
            horse.selector = horse_html

            selected_tab_text = horse_html.xpath(
                '//div[@class="tab-row"]//li[contains(@class,"selected")]//text()').get()

            if collect_basic:
                # information available in all tabs, only collected once
                horse.add_xpath('name', '//h1/span[@class="notranslate"]')
                horse.add_xpath('country', '//h1/span[@class="notranslate"]')
                horse.add_xpath('registration', '//h1/span[@class="comment"]')
                horse.add_xpath('ueln', '//h1/span[contains(@class,"ueln")]')
                horse.add_xpath('sex', '//div[@id="content"]/div/table[@class="latte"][1]//td[2]')
                horse.add_xpath('birthdate', '//table[@class="latte"][1]//td[3]')
                horse.add_xpath('breeder', '//table[@class="latte"][2]//td[2]')
                horse.add_xpath('chip', '//strong[contains(text(),"Microchipkode")]//following-sibling::span')

                collect_basic = False

            if selected_tab_text == 'Afstamning':
                # Pedigree information
                ancestors = [handle_cell(x) for x in
                    horse_html.xpath('//table[@id="horseDescent"]//td')]

                add_parents(ancestors[1], ancestors[2], ancestors[3])
                add_parents(ancestors[4], ancestors[5], ancestors[6])
                add_parents(ancestors[8], ancestors[9], ancestors[10])
                add_parents(ancestors[11], ancestors[12], ancestors[13])

                add_parents(ancestors[0], ancestors[1], ancestors[4])
                add_parents(ancestors[7], ancestors[8], ancestors[11])

                add_parents(horse, ancestors[0], ancestors[7])

            elif selected_tab_text == 'Væddeløbsresultater':
                # Racing career
                summary_table = horse_html.xpath('(//table[@class="latte"])[last()]')

                for summary_row in summary_table.xpath('.//tr')[ 1 : ]:

                    columns_text = [remove_tags(x.get()) for x in summary_row.xpath('./td')]

                    if columns_text[1] == '0':
                        continue

                    wins, place, show = [int(x) if x.isdigit() else 0
                        for x in columns_text[2].split('-')]

                    horse.add_value('start_summary', {
                        'year': int(columns_text[0]) if columns_text[0].isdigit() else 0,
                        'starts': int(columns_text[1]),
                        'wins': wins,
                        'place': place,
                        'show': show,
                        'purse': int(columns_text[3].replace(' kr', '').replace(' ', '')),
                        'mark': columns_text[4]
                    })

                for start_row in horse_html.xpath('//table[contains(@class,"latte_tight")]//tr')[ 1 : ]:
                    columns_text = [remove_tags(x.get()) for x in start_row.xpath('./td')]

                    start = {
                        'racetrack_code': columns_text[0],
                        'racetype': 'qualifier' if columns_text[2] == 'k' else 'race',
                        'started': True,
                        'disqualified': False,
                        'dnf': False,
                        'monte': False,
                        'gallop': False,
                        'startmethod': 'standing',
                        'driver': columns_text[-2].strip(),
                        'purse': int(columns_text[-1].replace(' ', ''))
                    }

                    if start_row.xpath('.//td[2]/a/@href'):
                        start['link'] = start_row.xpath('.//td[2]/a/@href').extract_first()

                    date_string = columns_text[1]

                    if '-' in date_string:
                        start['racenumber'] = int(date_string[ date_string.find('-') + 1 : ])
                        date_string = date_string[ : date_string.find('-') ]

                    racedate = '-'.join(date_string[x : x + 2] for x in range(0, len(date_string), 2))

                    if int(date_string[0]) < 8:
                        racedate = '20' + racedate
                    else:
                        racedate = '19' + racedate

                    start['racedate'] = racedate

                    dist_string = columns_text[3]

                    if '/' in dist_string:
                        start['postposition'] = dist_string[ : dist_string.find('/') ]
                        dist_string = dist_string[ dist_string.find('/') + 1 : ]

                    start['distance'] = int(''.join([x for x in dist_string if x.isdigit()]))

                    if len(columns_text) == 8:
                        start['started'] = False

                    else:
                        if 'd' in columns_text[4]:
                            start['disqualified'] = True

                        racetime = columns_text[5].replace(',', '.')

                        if racetime[0] == 'm':
                            start['monte'] = True
                            racetime = racetime[ 1 : ]

                        if '.' in racetime:
                            start['racetime'] = float(''.join([x for x in racetime if x.isdigit() or x == '.']))
                            racetime = racetime.replace(str(start['racetime']), '')

                        if 'opg' in racetime:
                            start['dnf'] = True
                            racetime = racetime.replace('opg', '')

                        if 'a' in racetime:
                            start['startmethod'] = 'mobile'
                            racetime = racetime.replace('a', '')
                        elif 'l' in racetime:
                            start['startmethod'] = 'line'
                            racetime = racetime.replace('l', '')

                        if 'g' in racetime:
                            start['gallop'] = True
                            racetime = racetime.replace('g', '')

                        if len(racetime) != 0:
                            start['disqstring'] = racetime


                        if columns_text[4].isdigit():
                            start['finish'] = int(columns_text[4])

                    if start['racetype'] == 'qualifier':
                        start['approved'] = columns_text[6][ : 2 ] == 'gk'
                    elif columns_text[6].isdigit():
                        start['ev_odds'] = int(columns_text[6])

                    horse.add_value('starts', start)

            elif selected_tab_text == 'Afkom':
                # Offspring to the horse
                rows = horse_html.xpath('//table[@class="green expand"]//tr')[ 1 : ]
                for row in rows:
                    if len(row.xpath('./td')) == 1:
                        offspring.selector = row

                        offspring.add_xpath('registration', './/span[1]')

                        if horse.get_output_value('sex') == 'mare':
                            if row.xpath('.//a[1]'):
                                sire = ItemLoader(item=HorseItem(), selector=row)

                                sire.add_xpath('name', './/a[1]/span')
                                sire.add_xpath('country', './/a[1]/span')
                                sire.add_xpath('link', './/a[1]/@href')
                                sire.add_value('sex', 'horse')

                                offspring.add_value('sire', sire.load_item())

                            outfile = f'{offspring.get_output_value("link")}.json'

                            if (not os.path.exists(os.path.join(JSON_DIRECTORY, 'horses', outfile)) and
                                    offspring.get_output_value('link')):
                                yield SplashRequest(
                                    url = BASE_URL.format(offspring.get_output_value('link')),
                                    callback = self.parse,
                                    endpoint = 'execute',
                                    args= {
                                        'wait': 5,
                                        'lua_source': self.lua_source
                                    }
                                )


                        else:
                            if row.xpath('.//a[1]'):
                                dam = ItemLoader(item=HorseItem(), selector=row)

                                dam.add_xpath('name', './/a[1]/span')
                                dam.add_xpath('country', './/a[1]/span')
                                dam.add_xpath('link', './/a[1]/@href')
                                dam.add_value('sex', 'mare')

                                if row.xpath('.//a[2]'):
                                    dam_sire = ItemLoader(item=HorseItem(), selector=row)

                                    dam_sire.add_xpath('name', './/a[2]/span')
                                    dam_sire.add_xpath('country', './/a[2]/span')
                                    dam_sire.add_xpath('link', './/a[2]/@href')
                                    dam_sire.add_value('sex', 'horse')

                                    dam.add_value('sire', dam_sire.load_item())

                                offspring.add_value('dam', dam.load_item())


                        horse.add_value('offspring', offspring.load_item())

                    else:
                        offspring = ItemLoader(item=HorseItem(), selector=row)

                        offspring.add_xpath('birthdate', './td[2]')
                        offspring.add_xpath('name', './/span[@class="notranslate"]')
                        offspring.add_xpath('country', './/span[@class="notranslate"]')
                        offspring.add_xpath('link', './/a/@href')
                        offspring.add_xpath('sex', './td[4]')

                        starts = row.xpath('.//td[5]/text()').extract_first()

                        if starts not in ['0', '', None]:
                            wins, place, show = [int(x) if x.isdigit() else 0 for x in
                                row.xpath('.//td[6]/text()').extract_first().split('-')]

                            standing = row.xpath('.//td[7]/text()').extract_first()
                            mobile = row.xpath('.//td[8]/text()').extract_first()

                            mark = ' '.join([standing, mobile]).strip()

                            purse = row.xpath('.//td[9]/text()').extract_first()

                            offspring.add_value('start_summary', {
                                'year': 0,
                                'starts': int(starts),
                                'wins': wins,
                                'place': place,
                                'show': show,
                                'mark': mark,
                                'purse': int(purse.replace(' kr.').replace(' ', ''))
                            })

        yield horse.load_item()
