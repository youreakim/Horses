from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags
from scrapy_splash import SplashRequest

from france.items import HorseItem

import datetime
import json
import os

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/france'

BASE_URL = 'https://www.letrot.com/stats/fiche-cheval/{}/'


def parse_pedigree(html, horse):
    # the pedigree is five generations deep
    # all ancestors have an id the denotes generation and a value for where it
    # is placed, 1 at the top, 2**generation at the bottom, if the second number
    # is odd it is a sire, else a dam
    cells = html.xpath('//div[@class="root"]//a[contains(@id,"_")]')
    cells = {x.attrib['id']: handle_cell(x) for x in cells}

    add_parents(cells.get('4_1', None), cells.get('5_1', None), cells.get('5_2', None))
    add_parents(cells.get('4_2', None), cells.get('5_3', None), cells.get('5_4', None))
    add_parents(cells.get('4_3', None), cells.get('5_5', None), cells.get('5_6', None))
    add_parents(cells.get('4_4', None), cells.get('5_7', None), cells.get('5_8', None))
    add_parents(cells.get('4_5', None), cells.get('5_9', None), cells.get('5_10', None))
    add_parents(cells.get('4_6', None), cells.get('5_11', None), cells.get('5_12', None))
    add_parents(cells.get('4_7', None), cells.get('5_13', None), cells.get('5_14', None))
    add_parents(cells.get('4_8', None), cells.get('5_15', None), cells.get('5_16', None))
    add_parents(cells.get('4_9', None), cells.get('5_17', None), cells.get('5_18', None))
    add_parents(cells.get('4_10', None), cells.get('5_19', None), cells.get('5_20', None))
    add_parents(cells.get('4_11', None), cells.get('5_21', None), cells.get('5_22', None))
    add_parents(cells.get('4_12', None), cells.get('5_23', None), cells.get('5_24', None))
    add_parents(cells.get('4_13', None), cells.get('5_25', None), cells.get('5_26', None))
    add_parents(cells.get('4_14', None), cells.get('5_27', None), cells.get('5_28', None))
    add_parents(cells.get('4_15', None), cells.get('5_29', None), cells.get('5_30', None))
    add_parents(cells.get('4_16', None), cells.get('5_31', None), cells.get('5_32', None))

    add_parents(cells.get('3_1', None), cells.get('4_1', None), cells.get('4_2', None))
    add_parents(cells.get('3_2', None), cells.get('4_3', None), cells.get('4_4', None))
    add_parents(cells.get('3_3', None), cells.get('4_5', None), cells.get('4_6', None))
    add_parents(cells.get('3_4', None), cells.get('4_7', None), cells.get('4_8', None))
    add_parents(cells.get('3_5', None), cells.get('4_9', None), cells.get('4_10', None))
    add_parents(cells.get('3_6', None), cells.get('4_11', None), cells.get('4_12', None))
    add_parents(cells.get('3_7', None), cells.get('4_13', None), cells.get('4_14', None))
    add_parents(cells.get('3_8', None), cells.get('4_15', None), cells.get('4_16', None))

    add_parents(cells.get('2_1', None), cells.get('3_1', None), cells.get('3_2', None))
    add_parents(cells.get('2_2', None), cells.get('3_3', None), cells.get('3_4', None))
    add_parents(cells.get('2_3', None), cells.get('3_5', None), cells.get('3_6', None))
    add_parents(cells.get('2_4', None), cells.get('3_7', None), cells.get('3_8', None))

    add_parents(cells.get('1_1', None), cells.get('2_1', None), cells.get('2_2', None))
    add_parents(cells.get('1_2', None), cells.get('2_3', None), cells.get('2_4', None))

    add_parents(horse, cells.get('1_1', None), cells.get('1_2', None))


def handle_cell(cell):
    if remove_tags(cell.get()) == '-':
        return

    horse = ItemLoader(item=HorseItem(), selector=cell)

    horse.add_xpath('name', '.')
    horse.add_xpath('country', '.')
    horse.add_xpath('link', './@href')
    horse.add_value('sex', 'horse' if int(cell.attrib['id'][-1]) % 2 == 1 else 'mare')

    return horse


def add_parents(horse, sire, dam):
    if horse is not None:
        if sire is not None:
            horse.add_value('sire', sire.load_item())

        if dam is not None:
            horse.add_value('dam', dam.load_item())


class HorseCollector(Spider):
    """
    Collects horses from 'letrot.com'
    Takes an link to start from and gets starts, career summary, pedigree, offspring
    and siblings, if the horse is a mare her offspring is also collected, all
    siblings are also collected.
    If the horse has not started or qualified the page is automatically redirected
    to the pedigree, that's why it's necessary to use SplashRequest
    """
    name = 'horsecollector'
    allowed_domains = ['letrot.com']


    def __init__(self, start_id='', *args, **kwargs):
        super(HorseCollector, self).__init__(*args, **kwargs)

        self.id = start_id


    def start_requests(self):
        yield SplashRequest(
            url=BASE_URL.format(self.id) + 'courses/dernieres-performances',
            callback=self.parse,
            cb_kwargs=dict(id=self.id),
            args={
                'wait': 5,
            }
        )

    def parse(self, response, id):
        horse = ItemLoader(item=HorseItem(), selector=response)

        horse.add_value('link', id)
        horse.add_xpath('name', '//div[@class="title-cheval__name"]')
        horse.add_xpath('country', '//div[@class="title-cheval__name"]')
        horse.add_xpath('sex', '//span[contains(text(),"Sexe")]//parent::div/text()')
        horse.add_xpath('birthdate', '//span[contains(text(),"Année")]//parent::div/text()')
        horse.add_xpath('breeder', '//span[contains(text(),"Eleveur")]//following-sibling::span')

        current_tab_text = response.xpath('//ul[@id="sub_sub_menu_fichecheval"]/li[@class="active"]//text()').get()

        if current_tab_text.lower() == 'dernières performances':
            # the horse has started
            for row in response.xpath('//table[@id="result_table"]/tbody/tr'):
                # the horse has only done a qualifier and no races
                if row.xpath('./td[@class="dataTables_empty"]'):
                    break

                racename = row.xpath('.//td[10]/text()').get()
                if racename and racename.strip() == 'QUALIFICATION':
                    start = {
                        'racetype': 'qualifier',
                        'trainer': row.xpath('.//td[6]/a/text()').get(),
                        'racetrack': row.xpath('.//td[8]/a/text()').get(),
                        'monte': 'M' == row.xpath('.//td[13]/a/text()').get(),
                        'approved': True,
                        'disqualified': False
                    }
                else:
                    start = {
                        'racetype': 'race',
                        'driver': row.xpath('.//td[5]/a/text()').get(),
                        'trainer': row.xpath('.//td[6]/a/text()').get(),
                        'racetrack': row.xpath('.//td[8]//text()').get(),
                        'direction': row.xpath('.//td[9]/text()').get(), #G == 'counterclockwise', D == 'clockwise'
                        'racename': row.xpath('.//td[10]//text()').get(),
                        'racecategory': row.xpath('.//td[12]/text()').get(),
                        'monte': 'M' == row.xpath('.//td[13]/text()').get(),
                        'purse': int(row.xpath('.//td[14]/span/text()').get()),
                        'startmethod': 'mobile' if row.xpath('.//td[17]/text()').get() == 'AUT' else 'standing',
                        'disqualified': 'D' in row.xpath('.//span[@class="bold"]/text()').get(),
                        'finish': (int(row.xpath('.//span[@class="bold"]/text()').get())
                            if row.xpath('.//span[@class="bold"]/text()').get().isdigit() else 0)
                    }

                start['racedate'] = row.xpath('./td[@class="sorting_1"]/@data-order').get()

                if start['disqualified']:
                    start['disqstring'] = row.xpath('.//span[@class="bold"]/text()').get()

                link = row.xpath('./td[10]/a/@href').get()

                if link and start['racetype'] == 'race':
                    link = link.split('/')
                    start['link'] = '/'.join(link[ link.index('stats') + 2 : link.index('stats') + 5 ])
                    start['country'] = 'FR'

                elif link:
                    link = link.split('/')
                    start['link'] = '/'.join(link[ link.index('qualification') : ])

                racetime = row.xpath('./td[2]/span/text()').get().strip()

                if racetime.isdigit() and len(racetime) == 4:
                    start['racetime'] = 60 * int(racetime[0]) + int(racetime[1:3]) + int(racetime[3]) / 10

                if start['racetrack'] == 'VINCENNES':
                    start['tracksize'] = row.xpath('.//td[16]/text()').get()

                horse.add_value('starts', start)

            yield Request(
                url=BASE_URL.format(id) + 'courses/carriere',
                callback=self.parse_career,
                cb_kwargs=dict(horse=horse, id=id)
            )

        else:
            parse_pedigree(response, horse)

            yield Request(
                url=BASE_URL.format(id) + 'elevage/production',
                callback=self.parse_offspring,
                cb_kwargs=dict(horse=horse, id=id)
            )


    def parse_career(self, response, horse, id):
        for row in response.xpath('//table[contains(@id,"result_table")]/tbody/tr'):
            # the horse has only done a qualifier and no races
            if row.xpath('./td[@class="dataTables_empty"]'):
                break

            year = row.xpath('.//td[1]//text()').get().strip()
            starts = int(row.xpath('.//td[2]/div/text()').get())
            wins = int(row.xpath('.//td[3]/div/text()').get())
            place = int(row.xpath('.//td[4]/div/text()').get())
            show = int(row.xpath('.//td[5]/div/text()').get())
            purse = int(row.xpath('.//td[6]/div/text()').get().replace('€', '').replace(' ', ''))

            horse.add_value('start_summary', {
                'year': int(year) if year.isdigit() else 0,
                'starts': starts,
                'wins': wins,
                'place': place,
                'show': show,
                'purse': purse,
                'mark': row.xpath('./td[7]/text()').get()
            })

        yield SplashRequest(
            url=BASE_URL.format(id) + 'elevage/pedigree',
            callback=self.parse_pedigree,
            cb_kwargs=dict(horse=horse, id=id),
            args={
                'wait': 5,
            }
        )


    def parse_pedigree(self, response, horse, id):
        parse_pedigree(response, horse)

        yield Request(
            url=BASE_URL.format(id) + 'elevage/production',
            callback=self.parse_offspring,
            cb_kwargs=dict(horse=horse, id=id)
        )


    def parse_offspring(self, response, horse, id):
        # check if the horse has offspring
        if not response.xpath('//td[@class="dataTables_empty"]'):
            for row in response.xpath('//table[@id="result_table"]/tbody/tr'):
                offspring = ItemLoader(item=HorseItem(), selector=row)

                offspring.add_xpath('name', './td[1]/a')
                offspring.add_xpath('country', './td[1]/a')
                offspring.add_xpath('link', './td[1]/a/@href')
                offspring.add_xpath('birthdate', './td[2]/text()')
                offspring.add_xpath('sex', './td[3]/text()')

                if horse.get_output_value('sex') == 'mare' and row.xpath('./td[4]/a'):
                    sire = ItemLoader(item=HorseItem(), selector=row.xpath('./td[4]/a'))

                    sire.add_xpath('name', '.')
                    sire.add_xpath('country', '.')
                    sire.add_xpath('link', './@href')
                    sire.add_value('sex', 'horse')

                    if sire.get_output_value('name'):
                        offspring.add_value('sire', sire.load_item())

                    filename = offspring.get_output_value('link').split('/')[1] + '.json'

                    if not os.path.exists(os.path.join(JSON_DIRECTORY, 'horses', filename)):
                        yield SplashRequest(
                            url=BASE_URL.format(offspring.get_output_value('link')) + 'courses/dernieres-performances',
                            callback=self.parse,
                            cb_kwargs=dict(id=offspring.get_output_value('link'))
                        )

                elif row.xpath('./td[4]/a'):
                    dam = ItemLoader(item=HorseItem(), selector=row.xpath('./td[4]/a'))

                    dam.add_xpath('name', '.')
                    dam.add_xpath('country', '.')
                    dam.add_xpath('link', './@href')
                    dam.add_value('sex', 'mare')

                    if row.xpath('./td[5]/a'):
                        dam_sire = ItemLoader(item=HorseItem(), selector=row.xpath('./td[5]/a'))

                        dam_sire.add_xpath('name', '.')
                        dam_sire.add_xpath('country', '.')
                        dam_sire.add_xpath('link', './@href')
                        dam_sire.add_value('sex', 'horse')

                        if dam_sire.get_output_value('name'):
                            dam.add_value('sire', dam_sire.load_item())

                    if dam.get_output_value('name'):
                        offspring.add_value('dam', dam.load_item())

                horse.add_value('offspring', offspring.load_item())

        yield Request(
            url=BASE_URL.format(id) + 'elevage/freres-soeurs-uterins',
            callback=self.parse_siblings,
            cb_kwargs=dict(horse=horse, id=id)
        )


    def parse_siblings(self, response, horse, id):
        dam_offspring = []

        for row in response.xpath('//table[@id="result_table"]/tbody/tr'):
            # should add some check so it does not add the horse to dam_offspring
            offspring = ItemLoader(item=HorseItem(), selector=row)

            offspring.add_xpath('name', './td[1]/a')
            offspring.add_xpath('country', './td[1]/a')
            offspring.add_xpath('link', './td[1]/a/@href')
            offspring.add_xpath('birthdate', './td[2]')
            offspring.add_xpath('sex', './td[3]')

            if row.xpath('./td[4]/a'):
                sire = ItemLoader(item=HorseItem(), selector=row.xpath('./td[4]/a'))

                sire.add_xpath('name', '.')
                sire.add_xpath('country', '.')
                sire.add_xpath('link', './@href')
                sire.add_value('sex', 'horse')

                offspring.add_value('sire', sire.load_item())

            start_summary = {
                'year': 0,
                'purse': int(row.xpath('./td[7]/div/text()').get().replace('€', '').replace(' ', ''))
            }

            attele_mark = row.xpath('./td[5]/text()').get()
            monte_mark = row.xpath('./td[6]/text()').get()

            if attele_mark and monte_mark and start_summary['purse'] != 0:
                start_summary['mark'] = f'{attele_mark} m{monte_mark}'

                offspring.add_value('start_summary', start_summary)

            filename = offspring.get_output_value('link').split('/')[1] + '.json'

            if not os.path.exists(os.path.join(JSON_DIRECTORY, 'horses', filename)):
                yield SplashRequest(
                    url=BASE_URL.format(offspring.get_output_value('link')) + 'courses/dernieres-performances',
                    callback=self.parse,
                    cb_kwargs=dict(id=offspring.get_output_value('link'))
                )

            dam_offspring.append(offspring)

        horse = horse.load_item()

        if len(dam_offspring) != 0:
            horse['dam']['offspring'] = [dict(x.load_item()) for x in dam_offspring]

        #yield horse
        print(horse)
