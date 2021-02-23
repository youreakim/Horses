from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.loader import ItemLoader
from scrapy_splash import SplashRequest
from scrapy.selector import Selector
from w3lib.html import remove_tags

from spain.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

import datetime
import os

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/spain'
BASE_URL = 'https://www.federaciobaleardetrot.com/'
CALENDAR_URL = BASE_URL + 'calendarioHipodromo.php?id={}&anyoActual={}'
RACEDAY_URL = BASE_URL + 'carreras_por_dia.php?idPrograma={}'
RACE_URL = BASE_URL + 'participantes_por_carrera.php?id={}&pagina=1'


class StartlistcollectorSpider(Spider):
    """
    Collects startlists from 'https://www.federaciobaleardetrot.com'.
    """
    name = 'startlistcollector'
    allowed_domains = ['www.federaciobaleardetrot.com']


    def __init__(self, *args, **kwargs):
        super(StartlistcollectorSpider, self).__init__(*args, **kwargs)
        self.start_date = datetime.date.today() + datetime.timedelta(days = 1)
        self.end_date = datetime.date.today() + datetime.timedelta(days = 5)


    def start_requests(self):
        yield Request(
                url=BASE_URL + 'resultados.php',
                callback=self.parse)


    def parse(self, response):
        for racetrack_link in response.xpath('//a[@class="titol"]'):
            racetrack = remove_tags(racetrack_link.get()).strip()

            track_id = racetrack_link.attrib['href']
            track_id = track_id[ track_id.find('(') + 1 : track_id.find(',') ]

            for year in range(self.start_date.year, self.end_date.year + 1):
                yield Request(
                        url=CALENDAR_URL.format(track_id, year),
                        callback=self.parse_calendar,
                        meta={'racetrack_code': track_id, 'racetrack': racetrack})


    def parse_calendar(self, response):
        for raceday_link in response.xpath('//td[@class="realizar"]/a/@href').getall():
            link_date = raceday_link[ raceday_link.rfind('=') + 1 : ]

            raceday_date = datetime.date(*reversed([int(x) for x in link_date.split('-')]))

            if self.start_date <= raceday_date <= self.end_date:
                raceday = ItemLoader(item=RacedayItem())

                raceday.add_value('date', raceday_date.strftime('%Y-%m-%d'))
                raceday.add_value('racetrack', response.meta['racetrack'])
                raceday.add_value('racetrack_code', response.meta['racetrack_code'])
                raceday.add_value('status', 'startlist')

                # click on the 'Ver condiciones'
                # link for each race to get the full conditions for that race
                yield SplashRequest(
                        url=BASE_URL + raceday_link,
                        callback=self.parse_raceday,
                        cb_kwargs=dict(raceday=raceday),
                        endpoint='execute',
                        args={
                            'wait': 5,
                            'lua_source': """
                                          treat = require('treat')
                                          function main(splash, args)
                                            splash:set_viewport_size(1600,1000)
                                            html_list = {}
                                            assert(splash:go(args.url))
                                            assert(splash:wait(2))
                                            html_list[#html_list + 1] = splash:html()
                                            conditions_links = splash:select_all('table.table a[href^="javascript:abrirCondiciones"]')
                                            for _, link in ipairs(conditions_links) do
                                                link:mouse_click()
                                                assert(splash:wait(1))
                                                html_list[#html_list + 1] = splash:html()
                                                splash:mouse_click(10, 10)
                                                assert(splash:wait(0.5))
                                            end
                                            return treat.as_array(html_list)
                                          end
                                          """
                        })


    def parse_raceday(self, response, raceday):
        races = []

        page_html = Selector(text=response.data[0])

        if page_html.xpath('//small/a[@class="btn"]'):
            day_link = page_html.xpath('//a[text()="Ver condiciones programa"]/@href').get()

            raceday.add_value('link', day_link[ day_link.find('(') + 1 : day_link.find(')')])

            for race_row in page_html.xpath('//table[contains(@class,"table-bordered")]//tr')[ 1 : ]:
                race = ItemLoader(item=RaceItem(), selector=race_row)

                race.add_xpath('link', './td[1]//@href')
                race.add_xpath('racenumber', './td[1]/p/a/text()')
                race.add_xpath('racename', './td[2]/a')
                race.add_xpath('startmethod', './td[4]')
                race.add_xpath('distance', './td[6]')

                cond_html = Selector(text=response.data[race.get_output_value('racenumber')])

                race.add_value('conditions',
                        remove_tags(cond_html.xpath('//div[@class="modal-Condiciones"]//div[@class="row"][2]').get()))

                races.append(race)

            yield Request(
                    url=RACE_URL.format(races[0].get_output_value('link')),
                    callback=self.parse_race,
                    cb_kwargs=dict(raceday=raceday),
                    meta={'races': races})


    def parse_race(self, response, raceday):
        races = response.meta['races']
        race = races.pop(0)

        starter_rows = response.xpath('//table[@id="Tablaparticipantes"]//tr[contains(@id,"aCabTR")]')

        for starter_row in starter_rows:
            starter = ItemLoader(item=RaceStarterItem(), selector=starter_row)

            starter.add_xpath('startnumber', './td[1]')
            starter.add_xpath('driver', './td[8]')
            starter.add_xpath('trainer', './td[9]')
            starter.add_xpath('distance', './td[11]')

            horse = ItemLoader(item=HorseItem(), selector=starter_row)

            horse.add_xpath('name', './td[4]/a')
            horse.add_xpath('country', './td[4]/a')
            horse.add_xpath('link', './td[4]//@href')
            horse.add_xpath('sex', './td[7]')
            horse.add_xpath('birthdate', './td[6]')

            pedigree_row = response.xpath(
                f'//td[2]/a[contains(@href,"id={horse.get_output_value("link")}")]//ancestor::tr')

            sire = ItemLoader(item=HorseItem(), selector=pedigree_row.xpath('./td[3]/a'))

            sire.add_xpath('name', '.')
            sire.add_xpath('country', '.')
            sire.add_xpath('link', './@href')
            sire.add_value('sex', 'horse')

            horse.add_value('sire', sire.load_item())

            dam = ItemLoader(item=HorseItem(), selector=pedigree_row.xpath('./td[4]/a'))

            dam.add_xpath('name', '.')
            dam.add_xpath('country', '.')
            dam.add_xpath('link', './@href')
            dam.add_value('sex', 'mare')

            dam_sire = ItemLoader(item=HorseItem(), selector=pedigree_row.xpath('./td[5]/a'))

            dam_sire.add_xpath('name', '.')
            dam_sire.add_xpath('country', '.')
            dam_sire.add_xpath('link', './@href')
            dam_sire.add_value('sex', 'horse')

            dam.add_value('sire', dam_sire.load_item())
            horse.add_value('dam', dam.load_item())

            horse.add_value('breeder', pedigree_row.xpath('./td[8]/text()').get())

            starter.add_value('horse', horse.load_item())

            race.add_value('starters', starter.load_item())

        raceday.add_value('races', race.load_item())

        if len(races) == 0:
            yield raceday.load_item()

        else:
            yield Request(
                    url=RACE_URL.format(races[0].get_output_value('link')),
                    callback=self.parse_race,
                    cb_kwargs=dict(raceday=raceday),
                    meta={'races': races})
