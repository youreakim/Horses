from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from holland.items import RacedayItem, RaceItem, TrotRaceStarterItem, GallopRaceStarterItem, HorseItem

from scrapy_splash import SplashRequest

from datetime import date, timedelta, datetime
import os

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/holland'

BASE_URL = 'https://www.ndr.nl'
CALENDAR_BODY = 'action=zoek_koersen&archief=true&jaar={}&maand={}'
RACEDAY_BODY = 'action=do_search&koersdag={}&koersnr={}&isAgenda=0&paard=false'


class ResultCollector(Spider):
    """
    Collects race results from 'https://www.ndr.nl'.
    Takes a start_date and an end_date, in the form 'yyyy-mm-dd', these default
    to yesterday.
    """
    name = 'resultcollector'
    allowed_domains = ['ndr.nl']

    def __init__(self, start_date = '', end_date = '', *args, **kwargs):
        super(ResultCollector, self).__init__(*args, **kwargs)
        yesterday = date.today() - timedelta(days = 1)
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date != '' else yesterday
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date != '' else yesterday


    def start_requests(self):
        current_date = self.start_date

        while current_date <= self.end_date:
            body = CALENDAR_BODY.format(current_date.year, current_date.month)
            yield SplashRequest(
                    url=BASE_URL + '/wp-admin/admin-ajax.php',
                    callback=self.parse,
                    args={'wait': 5,
                          'http_method': 'POST',
                          'body': body},
                    meta={'current_date': current_date}
            )

            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year+1, month=1, day=1)
            else:
                current_date = current_date.replace(month=current_date.month+1, day=1)


    def parse(self, response):
        for item in response.xpath('//li'):
            current_year = response.meta['current_date'].year
            date_string = item.xpath('./div/text()').get()
            date_splits = [int(x) for x in date_string.split('-')]

            raceday_date = date(current_year, date_splits[1], date_splits[0])

            if self.start_date <= raceday_date <= self.end_date:
                raceday = ItemLoader(item=RacedayItem(), selector=item)

                raceday.add_value('date', raceday_date.strftime('%Y-%m-%d'))
                raceday.add_xpath('link', './@data-koersdag')
                raceday.add_xpath('racetrack', './div[@class="ndr-agenda-baan"]')

                filename = '_'.join([raceday.get_output_value('date').replace('-', '_'),
                            raceday.get_output_value('racetrack').lower()]) + '.json'

                if not os.path.exists(os.path.join(JSON_DIRECTORY, 'result', filename)):
                    body = RACEDAY_BODY.format(raceday.get_output_value('link'),
                                                item.xpath('./@data-koersnr').get())

                    yield SplashRequest(
                            url=BASE_URL + '/wp-admin/admin-ajax.php',
                            callback=self.parse_raceday,
                            cb_kwargs=dict(raceday=raceday),
                            args={'wait': 5,
                                  'http_method': 'POST',
                                  'body': body}
                    )


    def parse_raceday(self, response, raceday):
        for tab in response.xpath('//div[contains(@id,"ndr-tab")]'):
            race = ItemLoader(item=RaceItem(), selector=tab)

            race.add_value('status', 'result')
            race.add_xpath('racenumber', './/div[@class="ndr-koers-naam"]')
            race.add_xpath('racename', './/h2')
            race.add_xpath('conditions', './/span[@class="ndr-koers-omschrijving"]')
            race.add_xpath('distance', './/span[@class="ndr-koers-datum-baan"][2]')
            race.add_xpath('startmethod', './/span[@class="ndr-koers-datum-baan"][2]')
            race.add_xpath('gait', './/span[@class="ndr-koers-datum-baan"][2]')

            for order, starter_row in enumerate(tab.xpath('.//tr[@data-type="draf"]'), 1):
                starter = ItemLoader(item=TrotRaceStarterItem(), selector=starter_row)

                starter.add_value('order', order)
                starter.add_value('started', True)
                starter.add_xpath('finish', './td[1]')
                starter.add_xpath('disqualified', './td[1]')
                starter.add_xpath('racetime', './td[3]')
                starter.add_xpath('purse', './td[4]')
                starter.add_xpath('driver', './td[5]')
                starter.add_xpath('distance', './td[6]')
                starter.add_xpath('ev_odds', './td[7]')
                starter.add_xpath('startnumber', './td[8]')

                horse = ItemLoader(item=HorseItem(), selector=starter_row)

                horse.add_xpath('name', './td[2]')
                horse.add_xpath('country', './@data-id')
                horse.add_xpath('link', './@data-id')

                starter.add_value('horse', horse.load_item())

                race.add_value('starters', starter.load_item())

            scratches = tab.xpath('.//p[contains(text(),"Niet gestart")]/text()').get()

            if scratches:
                for scratched in scratches[ scratches.find(':') + 1 : ].split(','):
                    order += 1
                    starter = ItemLoader(item=TrotRaceStarterItem())

                    starter.add_value('started', False)
                    starter.add_value('order', order)

                    horse = ItemLoader(item=HorseItem())

                    horse.add_value('name', scratched)
                    horse.add_value('country', scratched)

                    starter.add_value('horse', horse.load_item())

                    race.add_value('starters', starter.load_item())

            raceday.add_value('races', race.load_item())

        yield raceday.load_item()
