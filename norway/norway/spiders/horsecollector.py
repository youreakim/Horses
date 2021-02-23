from scrapy.spiders import Spider
from scrapy_splash import SplashRequest
from scrapy.selector import Selector
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags

from norway.items import HorseItem

BASE_URL = 'http://www.travsport.no/Andre-elementer/Sok-etter-hestkusklop/Sok-etter-hest/'


def handle_pedigree_cell(cell):
    if not cell.xpath('./a/text()').get():
        return None

    ancestor = ItemLoader(item=HorseItem(), selector=cell)

    ancestor.add_xpath('name', './a')
    ancestor.add_xpath('country', './a')
    ancestor.add_xpath('registration', './span[1]')
    ancestor.add_xpath('link', './span[1]')
    ancestor.add_value('sex', 'horse' if cell.attrib['class'] == 'fatherCell' else 'mare')

    return ancestor


def add_parents(horse, sire, dam):
    if horse is not None:
        if sire is not None:
            horse.add_value('sire', sire.load_item())

        if dam is not None:
            horse.add_value('dam', dam.load_item())


class HorseCollector(Spider):
    """
    Collects horses from 'travsport.no'
    Use an id (registration number or ueln where available) or a name and the name
    of the dam (in case there is multiple horses with the same name) as the starting
    point.
    Starts with that horse and collects pedigree, offspring, starts and start summary.
    If the horse is a mare and has offspring, those are also collected.
    """
    name = 'horsecollector'
    allowed_domains = ['travsport.no']

    def __init__(self, name = '', dam = '', start_id = '', *args, **kwargs):
        super(HorseCollector, self).__init__(*args, **kwargs)
        self.name = name.lower()
        self.dam = dam.lower()
        self.id = start_id
        self.lua_source = """
                             treat = require('treat')
                             function getHorsePages(splash)
                                local tabIdPrefix = 'ctl00_MainRegion_horseInfo_cell'
                                local ids = {'Avkom', 'Karriere', 'Starter', 'Stamtavle'}
                                local whichTabs = {
                                    ['Avkom'] = true,
                                    ['Karriere'] = true,
                                    ['Starter'] = true,
                                    ['Stamtavle'] = true
                                }
                                local savedHtml = {}
                                local currentlyOpen = splash:select('td.selected a'):text()
                                if whichTabs[currentlyOpen] then
                                    savedHtml[#savedHtml + 1] = splash:html()
                                    whichTabs[currentlyOpen] = false
                                end
                                for i, v in ipairs(ids) do
                                    local opening = splash:select('td#' .. tabIdPrefix .. v .. ' a')
                                    if (opening and whichTabs[opening:text()]) then
                                        local ok, reason = opening:mouse_click()
                                        if ok then
                                            assert(splash:wait(4))
                                            savedHtml[#savedHtml + 1] = splash:html()
                                        end
                                    end
                                end
                                return treat.as_array(savedHtml)
                             end

                             function main(splash, args)
                                assert(splash:go(args.url))
                                assert(splash:wait(4.0))
                                local searchResult = splash:select_all('#ctl00_MainRegion_horseSearch_dgHester tr')
                                local htmlList = {}
                                if #searchResult > 0 then
                                    local searchLength = #searchResult
                                    local row
                                    local horseHtml
                                    for i = 2, searchLength do
                                        row = searchResult[i]
                                        local links = row:querySelectorAll('a')
                                        if #links > 2 then
                                            local horseName = links[1]:text():lower()
                                            i, j = string.find(horseName, '% %(')
                                            if i then
                                                horseName = string.sub(horseName, i)
                                            end
                                            local damName = links[3]:text():lower()
                                            k, l = string.find(damName, '% %(')
                                            if k then
                                                damName = string.sub(damName, k)
                                            end
                                            if horseName == args.horseName and damName == args.damName then
                                                row:querySelector('a').click()
                                                assert(splash:wait(3))
                                                horseHtml = getHorsePages(splash)
                                                htmlList[#htmlList + 1] = horseHtml
                                                assert(splash:go(args.url))
                                                assert(splash:wait(3))
                                                searchResult = splash:select_all('#ctl00_MainRegion_horseSearch_dgHester tr')
                                            end
                                        end
                                    end
                                else
                                    local html = getHorsePages(splash)
                                    htmlList[#htmlList + 1] = html
                                end
                                return treat.as_array(htmlList)
                             end
                             """


    def start_requests(self):
        if self.id != '':
            yield SplashRequest(
                url=BASE_URL + '?regNo=' + self.id,
                callback=self.parse,
                args={'wait': 5,
                      'lua_source': self.lua_source},
                endpoint='execute'
            )

        elif self.name != '':
            yield SplashRequest(
                url=BASE_URL + '?modus=0&search=' + self.name.replace(' ', '+'),
                callback=self.parse,
                args={'wait': 5,
                      'lua_source': self.lua_source,
                      'horseName': self.name,
                      'damName': self.dam},
                endpoint='execute'
            )


    def parse(self, response):
        for horse_list in response.data:
            horse = ItemLoader(item=HorseItem())

            header = True

            for html in horse_list:
                page_html = Selector(text=html)
                if header:
                    # the header information is available in all tabs, process once
                    name_row = page_html.xpath('//span[@id="ctl00_MainRegion_horseInfo_lblNavn"]/text()').get()
                    name_text = name_row[ : name_row.rfind('(') ]

                    horse.add_value('name', name_text)
                    horse.add_value('breed', name_row[ name_row.rfind('(') + 1 : name_row.rfind(')') ])
                    horse.add_value('country', name_text)

                    infoline_text = page_html.xpath('//span[@class="infoLinje"]/text()').get()
                    registration = infoline_text[ : infoline_text.find('f.') ].strip()

                    if '(' in registration:
                        registration = registration[ : registration.find('(') ]

                    if len(registration) > 15:
                        registration = registration.replace('DNTs Eliteavlshoppe', '')

                    horse.add_value('link', registration)
                    horse.add_value('registration', registration)

                    if len(registration) == 15:
                        horse.add_value('ueln', registration)

                    birthyear = infoline_text[ infoline_text.find('f.') + 2 : infoline_text.find('f.') + 8 ].strip()

                    if birthyear.isdigit():
                        horse.add_value('birthdate', birthyear + '-01-01')

                    if 'hingst' in infoline_text:
                        horse.add_value('sex', 'horse')
                    elif 'hoppe' in infoline_text:
                        horse.add_value('sex', 'mare')
                    elif 'vallak' in infoline_text:
                        horse.add_value('sex', 'gelding')
                    elif self.gender != '':
                        horse.add_value('sex', self.gender)

                    horse.add_value('breeder',
                        page_html.xpath('//span[@id="ctl00_MainRegion_horseInfo_lblOppdretter"]/text()').get())

                    header = False

                current_page = page_html.xpath('//td[@class="selected"]/a/text()').get()

                if current_page == 'Avkom':
                    offspring_rows = page_html.xpath('//table[@class="dg"]//tr')

                    for row in offspring_rows[ 1 : ]:
                        columns = row.xpath('./td')
                        columns_text = [x.xpath('.//text()').get() for x in columns]

                        offspring = ItemLoader(item=HorseItem(), selector=row)

                        offspring.add_xpath('name', './td[1]/a')
                        offspring.add_xpath('country', './td[1]/a')

                        offspring.add_xpath('birthdate', './td[2]')

                        offspring.add_xpath('sex', './td[4]')

                        if horse.get_output_value('sex') == 'mare' and row.xpath('./td[14]/a'):
                            sire = ItemLoader(item=HorseItem(), selector=row.xpath('./td[14]/a'))

                            sire.add_xpath('name', '.')
                            sire.add_xpath('country', '.')
                            sire.add_value('sex', 'horse')

                            offspring.add_value('sire', sire.load_item())

                            yield SplashRequest(
                                url=BASE_URL + '?modus=0&search=' + offspring.get_output_value('name').replace(' ', '+'),
                                callback=self.parse,
                                args={'wait': 5,
                                      'lua_source': self.lua_source,
                                      'damName': horse.get_output_value('name').lower(),
                                      'horseName': offspring.get_output_value('name').lower(),
                                      'gender': offspring.get_output_value('sex')
                                      },
                                endpoint='execute'
                            )

                        elif row.xpath('./td[14]/a'):
                            dam = ItemLoader(item=HorseItem(), selector=row.xpath('./td[14]/a'))

                            dam.add_xpath('name', '.')
                            dam.add_xpath('country', '.')
                            dam.add_value('sex', 'horse')

                            offspring.add_value('dam', dam.load_item())

                        if row.xpath('./td[6]/text()').get() != '0':
                            standing_mark = row.xpath('./td[12]/text()').get()
                            mobile_mark = row.xpath('./td[13]/text()').get()

                            if mobile_mark:
                                mobile_mark = f'{mobile_mark.strip()}a'

                            offspring.add_value('start_summary', {
                                'year': 0,
                                'starts': int(row.xpath('./td[6]/text()').get()),
                                'wins': int(row.xpath('./td[7]/text()').get()),
                                'place': int(row.xpath('./td[8]/text()').get()),
                                'show': int(row.xpath('./td[9]/text()').get()),
                                'purse': int(row.xpath('./td[11]/text()').get().replace(' ', '')),
                                'mark': f'{standing_mark} - {mobile_mark}'
                            })

                        horse.add_value('offspring', offspring.load_item())

                elif current_page == 'Karriere':
                    carrier_rows = page_html.xpath('//table[@class="dg"]//tr')

                    for row in carrier_rows[ 1 : ]:
                        columns_text = [remove_tags(x.get()) for x in row.xpath('./td')]

                        horse.add_value('start_summary', {
                            'year': int(columns_text[0]),
                            'starts': int(columns_text[1]),
                            'wins': int(columns_text[2]),
                            'place': int(columns_text[3]),
                            'show': int(columns_text[4]),
                            'purse': int(columns_text[7].replace(' ', '').replace(',-', '')),
                            'mark': columns_text[6]
                        })

                elif current_page == 'Stamtavle':
                    pedigree_cells = page_html.xpath('//table[@id="Table4"]//td')

                    ancestors = [handle_pedigree_cell(x) for x in pedigree_cells]

                    # sire half of the pedigree
                    add_parents(ancestors[2], ancestors[3], ancestors[4])
                    add_parents(ancestors[5], ancestors[6], ancestors[7])
                    add_parents(ancestors[9], ancestors[10], ancestors[11])
                    add_parents(ancestors[12], ancestors[13], ancestors[14])

                    add_parents(ancestors[1], ancestors[2], ancestors[5])
                    add_parents(ancestors[8], ancestors[9], ancestors[12])

                    add_parents(ancestors[0], ancestors[1], ancestors[8])

                    # dam half of the pedigree
                    add_parents(ancestors[17], ancestors[18], ancestors[19])
                    add_parents(ancestors[20], ancestors[21], ancestors[22])
                    add_parents(ancestors[24], ancestors[25], ancestors[26])
                    add_parents(ancestors[27], ancestors[28], ancestors[29])

                    add_parents(ancestors[16], ancestors[17], ancestors[20])
                    add_parents(ancestors[23], ancestors[24], ancestors[27])

                    add_parents(ancestors[15], ancestors[16], ancestors[23])

                    add_parents(horse, ancestors[0], ancestors[15])

                elif current_page == 'Starter':
                    # if there is a link in the fourth column, this was a norwegian race
                    start_rows = page_html.xpath('//table[@id="ctl00_MainRegion_horseInfo_startsUC_dgStarter"]//tr')

                    starts = []

                    for row in start_rows[ 1 : ]:
                        columns = row.xpath('./td')
                        columns_text = [x.xpath('.//text()').get().strip() for x in columns]

                        start = {
                            'driver': columns_text[0],
                            'racetrack': columns_text[1],
                            'racedate': '-'.join(reversed(columns_text[2].split('.'))),
                            'racenumber': int(columns_text[3]) if columns_text[3].isdigit() else 0,
                            'distance': int(columns_text[4].replace(' ', '')),
                            'postposition': columns_text[5].replace('\xa0', ''),
                            'startnumber': int(columns_text[6]),
                            'has_link': row.xpath('./td[4]/a/@href').get() is not None
                        }

                        # was the horse scratched
                        if columns_text[8] == 'STR':
                            start['started'] = False
                        else:
                            start['disqualified'] = columns_text[8][0] == 'd'
                            start['gallop'] = 'G' in columns_text[11]

                            if ',' in columns_text[8]:
                                start['racetime'] = float(columns_text[8].replace('a', '').replace(',', '.'))
                            elif 'br' in columns_text[8]:
                                start['finished'] = False
                            elif start['disqualified']:
                                start['gallop'] = 'g' in columns_text[8]

                            start['started'] = True
                            start['finish'] = int(columns_text[9]) if columns_text[9].isdigit() else 0

                            if columns_text[12].isdigit():
                                start['ev_odds'] = int(columns_text[12])

                            start['purse'] = columns_text[13].replace(',-', '').replace(' ', '')

                        starts.append(start)

                    horse.add_value('starts', starts)

            yield horse.load_item()
