from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from scrapy_splash import SplashRequest

from holland.items import HorseItem


JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/holland'

BASE_URL = 'https://www.ndr.nl'
HORSE_BODY = 'action=do_search&categorie=paard&type=draf&id=+S120046'


def handle_cell(cell):
    horse = ItemLoader(item=HorseItem(), selector=cell)

    horse.add_xpath('name', './strong')

    if horse.get_output_value('name') == 'N.V.T.':
        return None

    horse.add_xpath('sex', './text()[1]')
    horse.add_xpath('birthdate', './*[contains(text(),"-")]')

    return horse


def add_parent(horse, sire, dam):
    if horse is not None:
        if sire is not None:
            horse.add_value('sire', sire.load_item())

        if dam is not None:
            horse.add_value('dam', dam.load_item())


class HorseCollector(Spider):
    """
    Collects information about horses from 'https://www.ndr.nl'.
    Takes a start_id, the horses dutch registration number.
    There are no links to ancestors, offspring is not shown, so the information
    that can be retrieved is very limited.
    """
    name = 'horsecollector'
    allowed_domains = ['ndr.nl']


    def __init__(self, start_id, *args, **kwargs):
        super(HorseCollector, self).__init__(*args, **kwargs)

        # if start_id[1].isdigit():
        #     start_id = '+' + start_id

        self.start_id = start_id


    def start_requests(self):
        yield SplashRequest(
                    url=BASE_URL + '/wp-admin/admin-ajax.php',
                    callback=self.parse,
                    args={'wait': 5,
                          'http_method': 'POST',
                          'body': HORSE_BODY.format(self.start_id)}
        )


    def parse(self, response):
        horse = ItemLoader(item=HorseItem(), selector=response)

        horse.add_xpath('name', '//label[text()="Naam"]//following-sibling::span')
        horse.add_xpath('registration', '//label[text()="Stamboeknummer"]//following-sibling::span')
        horse.add_xpath('sex', '//label[text()="Geslacht"]//following-sibling::span')
        horse.add_xpath('link', '//label[text()="Stamboeknummer"]//following-sibling::span')
        horse.add_xpath('country', '//label[text()="Stamboeknummer"]//following-sibling::span')
        horse.add_xpath('birthdate', '//label[text()="Geboortedatum"]//following-sibling::span')
        horse.add_xpath('breeder', '//label[text()="Fokker"]//following-sibling::span')

        for start_row in response.xpath('//div[@id="ndr-tab-verrichtingen"]//tbody/tr'):
            racedate = start_row.xpath('./td[1]/text()').get().split('-')
            racedate[2] = f'{"20" if int(racedate[2]) < 70 else "19"}{racedate[2]}'

            finish = start_row.xpath('./td[3]/text()').get()
            disqualified = 'A' in finish

            if disqualified or not finish.isdigit():
                disqstring = finish
                finish = 0

            else:
                finish = int(finish)

            racetime = start_row.xpath('./td[4]/text()').get()

            if racetime:
                racetime = int(racetime[0]) * 60 + int(racetime[2:4]) + int(racetime[5]) / 10
            else:
                racetime = 0

            ev_odds = start_row.xpath('./td[7]/text()').get()

            if ev_odds:
                ev_odds = float(ev_odds.replace(',', '.'))
            else:
                ev_odds = 0

            purse = start_row.xpath('./td[7]/text()').get()

            if purse:
                purse = int(''.join(x for x in purse if x.isdigit()))
            else:
                purse = 0

            horse.add_value('starts', {
                'link': start_row.xpath('./@date-koersdag').get(),
                'racedate': '-'.join(reversed(racedate)),
                'racetrack': start_row.xpath('./td[2]/text()').get().strip(),
                'finish': finish,
                'disqualified': disqualified,
                'racetime': racetime,
                'distance': int(start_row.xpath('./td[5]/text()').get()),
                'startmethod': 'mobile' if 'Autostart' in start_row.xpath('./td[6]/text()').get() else 'standing',
                'ev_odds': ev_odds,
                'driver': start_row.xpath('./td[8]/text()').get().strip(),
                'racenumber': int(start_row.xpath('./td[9]/text()').get()),
                'purse': purse
            })

        mark = ' / '.join([response.xpath('//label[text()="Recordtijd"]//following-sibling::text()').get(),
                response.xpath('//label[text()="Recordtijd afstand"]//following-sibling::text()').get()])

        horse.add_value('start_summary', {
            'year': 0,
            'purse': response.xpath('//label[text()="Belastbaar bedrag"]//following-sibling::text()').get(),
            'starts': response.xpath('//label[text()="Aantal gestart"]//following-sibling::text()').get(),
            'wins': response.xpath('//label[text()="Overwinningen totaal"]//following-sibling::text()').get(),
            'mark': mark
        })

        ancestors = [handle_cell(x) for x in
                response.xpath('//div[@id="ndr-tab-stamboom"]//td')]

        add_parent(ancestors[3], ancestors[4], ancestors[5])
        add_parent(ancestors[6], ancestors[7], ancestors[8])
        add_parent(ancestors[10], ancestors[11], ancestors[12])
        add_parent(ancestors[13], ancestors[14], ancestors[15])
        add_parent(ancestors[18], ancestors[19], ancestors[20])
        add_parent(ancestors[21], ancestors[22], ancestors[23])
        add_parent(ancestors[25], ancestors[26], ancestors[27])
        add_parent(ancestors[28], ancestors[29], ancestors[30])

        add_parent(ancestors[2], ancestors[3], ancestors[6])
        add_parent(ancestors[9], ancestors[10], ancestors[13])
        add_parent(ancestors[17], ancestors[18], ancestors[21])
        add_parent(ancestors[24], ancestors[25], ancestors[28])

        add_parent(ancestors[1], ancestors[2], ancestors[9])
        add_parent(ancestors[16], ancestors[17], ancestors[24])

        add_parent(horse, ancestors[1], ancestors[16])

        # yield horse.load_item()
        print(horse.load_item())
