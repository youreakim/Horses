from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from holland.items import RacedayItem, RaceItem, TrotRaceStarterItem, HorseItem

from scrapy_splash import SplashRequest

from datetime import date, timedelta
import os

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/holland'

BASE_URL = 'https://www.ndr.nl'
RACEDAY_BODY = 'action=do_search&koersdag={}&koersnr={}&isAgenda=0&paard=false'


class StartlistCollector(Spider):
    """
    Collects startlists from 'https://www.ndr.nl'.
    """
    name = 'startlistcollector'
    allowed_domains = ['ndr.nl']


    def __init__(self, *args, **kwargs):
        super(StartlistCollector, self).__init__(*args, **kwargs)
        self.start_date = date.today() + timedelta(days = 1)
        self.end_date = date.today() + timedelta(days = 6)


    def start_requests(self):
        yield SplashRequest(
                    url=BASE_URL + '/?page_id=3712',
                    callback=self.parse,
                    args={'wait': 5}
        )


    def parse(self, response):
        while self.start_date <= self.end_date:
            date_string = self.start_date.strftime('%d-%m-%y')

            for raceday_row in response.xpath(f'//div[text()="{date_string}"]//parent::li'):
                raceday = ItemLoader(item=RacedayItem(), selector=raceday_row)

                raceday.add_xpath('racetrack', './div[@class="ndr-agenda-baan"]')
                raceday.add_xpath('link', './@data-koersdag')
                raceday.add_value('date', self.start_date.strftime('%Y-%m-%d'))
                raceday.add_value('status', 'startlist')

                filename = '_'.join([raceday.get_output_value('date').replace('-', '_'),
                            raceday.get_output_value('racetrack').lower()]) + '.json'

                if not os.path.exists(os.path.join(JSON_DIRECTORY, 'startlist', filename)):
                    body = RACEDAY_BODY.format(
                            raceday.get_output_value('link'), raceday_row.xpath('./@data-koersnr').get())

                    yield SplashRequest(
                                url=BASE_URL + '/wp-admin/admin-ajax.php',
                                callback=self.parse_raceday,
                                cb_kwargs=dict(raceday=raceday),
                                args={'wait': 5,
                                      'http_method': 'POST',
                                      'body': body}
                    )

            self.start_date += timedelta(days=1)


    def parse_raceday(self, response, raceday):
        for tab in response.xpath('//div[contains(@id,"ndr-tab")]'):
            race = ItemLoader(item=RaceItem(), selector=tab)

            race.add_value('status', 'startlist')
            race.add_xpath('racenumber', './/div[@class="ndr-koers-naam"]')
            race.add_xpath('racename', './/h2')
            race.add_xpath('conditions', './/span[@class="ndr-koers-omschrijving"]')
            race.add_xpath('distance', './/span[@class="ndr-koers-datum-baan"][2]')
            race.add_xpath('startmethod', './/span[@class="ndr-koers-datum-baan"][2]')
            race.add_xpath('gait', './/span[@class="ndr-koers-datum-baan"][2]')

            for starter_row in tab.xpath('.//tr[@data-type="draf"]'):
                starter = ItemLoader(item=TrotRaceStarterItem(), selector=starter_row)

                starter.add_xpath('driver', './td[2]')
                starter.add_xpath('distance', './td[3]')
                starter.add_xpath('startnumber', './td[4]')

                horse = ItemLoader(item=HorseItem(), selector=starter_row)

                horse.add_xpath('name', './td[1]')
                horse.add_xpath('link', './@data-id')
                horse.add_xpath('country', './@data-id')

                starter.add_value('horse', horse.load_item())

                race.add_value('starters', starter.load_item())

            # if there are no starters, this startlist is not published
            # and therefor we do not add the race
            if race.get_output_value('starters'):
                raceday.add_value('races', race.load_item())

        if raceday.get_output_value('races'):
            yield raceday.load_item()
