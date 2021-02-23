from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags

from spain.items import RacedayItem, RaceItem, RaceStarterItem, HorseItem

import os


JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/spain'
BASE_URL = 'https://www.federaciobaleardetrot.com/'
HORSE_URL = BASE_URL + 'resultados_por_caballo.php?id={}&pagina=1'


def handle_ancestor_cell(cell, sex):
    if not cell.xpath('.//a'):
        return None

    horse = ItemLoader(item=HorseItem(), selector=cell)

    horse.add_xpath('name', './/a')
    horse.add_xpath('country', './/a')
    horse.add_xpath('link', './/a/@href')
    horse.add_xpath('birthdate', './/span[contains(text(),"/")]/text()[1]')
    horse.add_value('sex', sex)

    return horse


def add_parents(horse, sire, dam):
    if horse is not None:
        if sire is not None:
            horse.add_value('sire', sire.load_item())

        if dam is not None:
            horse.add_value('dam', dam.load_item())


class HorsecollectorSpider(Spider):
    """
    Collects horses from 'https://www.federaciobaleardetrot.com'.
    Takes a start_id to kick things off.
    Collect information about racing career, pedigree, and offspring. If the horse
    is a mare and has offspring, these are also collected.
    """
    name = 'horsecollector'
    allowed_domains = ['www.federaciobaleardetrot.com']

    def __init__(self, start_id, *args, **kwargs):
        super(HorsecollectorSpider, self).__init__(*args, **kwargs)
        self.start_id = start_id


    def start_requests(self):
        yield Request(
                    url=HORSE_URL.format(self.start_id),
                    callback=self.parse)


    def parse(self, response):
        horse = ItemLoader(item = HorseItem(), selector=response)

        horse.add_xpath('name', '//h4/span')
        horse.add_xpath('country', '//h4/span')
        horse.add_xpath('ueln', '//td[text()="Código:"]//following-sibling::td[1]')
        horse.add_xpath('birthdate', '//h3/small/span/text()[1]')
        horse.add_xpath('sex', '//td[text()="Sexo:"]//following-sibling::td[1]')
        horse.add_xpath('breeder', '//td[text()="Criador:"]//following-sibling::td')

        for descendant in response.xpath('//td[text()="Hijos:"]//following-sibling::td/a'):
            offspring = ItemLoader(item=HorseItem(), selector=descendant)

            offspring.add_xpath('name', '.')
            offspring.add_xpath('country', '.')
            offspring.add_xpath('link', './@href')

            horse.add_value('offspring', offspring.load_item())

            filename = f'{offspring.get_output_value("link")}.json'

            if (horse.get_output_value('sex') == 'mare' and
                    not os.path.exists(os.path.join(JSON_DIRECTORY, 'horses', filename))):
                yield Request(
                            url=HORSE_URL.format(offspring.get_output_value('link')),
                            callback=self.parse)

        ancestors = [handle_ancestor_cell(x, 'horse' if index % 2 == 0 else 'mare')
                for index, x in enumerate(response.xpath('//td[@class="recuadroTD"]'))]

        add_parents(ancestors[2], ancestors[6], ancestors[7])
        add_parents(ancestors[3], ancestors[8], ancestors[9])
        add_parents(ancestors[4], ancestors[10], ancestors[11])
        add_parents(ancestors[5], ancestors[12], ancestors[13])

        add_parents(ancestors[0], ancestors[2], ancestors[3])
        add_parents(ancestors[1], ancestors[4], ancestors[5])

        add_parents(horse, ancestors[0], ancestors[1])

        for start_row in response.xpath('//tr[contains(@id,"aCabTR")]'):
            racedate = remove_tags(start_row.xpath('./td[1]').get())
            racedate = '-'.join(reversed(racedate.split('-')))

            gallop = False

            if start_row.xpath('./td[4]/div'):
                gallop = 'GALOP' in start_row.xpath('./td[4]/div/text()').get()

            finish = start_row.xpath('./td[4]/text()').get().replace('.', '')

            startnumber = start_row.xpath('./td[3]//class[1]/text()').get()

            if ')' in startnumber:
                startnumber = startnumber[ startnumber.find('(') + 1 : startnumber.find(')')]

            purse = start_row.xpath('./td[9]/text()').get()

            if purse:
                purse = purse.replace('€', '').replace('.', '').strip()
            else:
                purse = ''

            distance = start_row.xpath('./td[6]/text()').get().replace('m', '').replace('.', '').strip()

            racetime = start_row.xpath('./td[8]/text()').get()

            if racetime:
                racetime = racetime.split()

                if len(racetime) == 3:
                    racetime = int(racetime[0][0]) * 60 + int(racetime[1][:2]) + int(racetime[2]) / 10
                else:
                    racetime = 0

            link = start_row.xpath('./td[2]//@href').get()
            link = link[ link.find('id=') + 3 : link.find('&pagina') ]

            driver = start_row.xpath('./td[3]//a/text()').get().strip()

            if driver == '-- --':
                driver = None

            horse.add_value('starts', {
                'racedate': racedate,
                'link': link,
                'racename': start_row.xpath('./td[2]/a/text()').get().strip(),
                'driver': driver,
                'startnumber': int(startnumber),
                'finish': int(finish) if finish.isdigit() else 0,
                'disqualified': 'D' in start_row.xpath('./td[4]/text()').get(),
                'gallop': gallop,
                'disqstring': start_row.xpath('./td[4]/div/text()').get(),
                'racetrack': start_row.xpath('./td[5]/text()').get(),
                'distance': int(distance),
                'racetime': racetime,
                'purse': int(purse) if purse.isdigit() else 0,
                'started': 'R' in start_row.xpath('./td[4]/text()').get()
            })

        for summary_row in response.xpath('//div[@id="resumen"]//tr'):
            if summary_row.xpath('./td[1]//*[text()="Año"]'):
                continue

            columns = [x.xpath('.//text()').get() for x in summary_row.xpath('./td')]
            columns = [int(x) if x and x.isdigit() else 0 for x in columns]

            horse.add_value('start_summary', {
                'year': columns[0],
                'wins': columns[1],
                'place': columns[2],
                'show': columns[3],
                'starts': columns[12] - columns[11],
                'mark': columns[13],
                'purse': columns[14],
            })

        yield horse.load_item()
