from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from scrapy.http import JsonRequest
from datetime import date

from norway.items import HorseItem, SummaryItem, RacelineItem

import json
import os


BASE_URL = 'https://www.rikstoto.no/api'
JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/norway'


def add_parents(horse, sire, dam):
    if horse is not None:
        if sire is not None:
            horse.add_value('sire', sire.load_item())

        if dam is not None:
            horse.add_value('dam', dam.load_item())


class HorseCollector(Spider):
    """
    Collects registration, pedigree and racing information for a horse specified
    by start_id (registration number). If the horse is a mare, her offspring
    will also be collected. Information retrieved from the API at 'rikstoto.no'.
    """
    name = 'horsecollector'
    allowed_domains = ['rikstoto.no', 'travsport.no']


    def __init__(self, start_id, *args, **kwargs):
        super(HorseCollector, self).__init__(*args, **kwargs)
        self.start_id = start_id


    def start_requests(self):
        """
        Get registration information for the horse specified by start_id.
        """
        yield JsonRequest(
            url=f'{BASE_URL}/infopanel/liferow/horse/{self.start_id}',
            callback=self.parse
        )


    def parse(self, response):
        """
        Parse the registration information and get career summary.
        """
        response_json = json.loads(response.body)

        horse_json = response_json['result']

        horse = ItemLoader(item=HorseItem())

        horse.add_value('name', horse_json['horseName'])
        horse.add_value('country', horse_json['horseName'])
        horse.add_value('registration', horse_json['horseRegistrationNumber'])
        horse.add_value('sex', horse_json['sex'])
        horse.add_value('breed', horse_json['breed'])
        horse.add_value('collection_date', date.today().strftime('%Y-%m-%d'))
        horse.add_value('birthdate', str(int(horse.get_output_value('collection_date')[:4]) - int(horse_json['age'][:-3])))
        horse.add_value('breeder', horse_json['breederName'])

        yield JsonRequest(
            url=f'{BASE_URL}/infopanel/career/horse/{horse.get_output_value("registration")}',
            callback=self.parse_summary,
            cb_kwargs=dict(horse=horse)
        )


    def parse_summary(self, response, horse):
        """
        Parse the career summary, if the horse has started, get the racelines
        for each year the horse has made any starts, else continue to the
        pedigree information.
        """
        response_json = json.loads(response.body)

        if len(response_json['result']) == 0:
            yield JsonRequest(
                url=f'{BASE_URL}/infopanel/pedigree/{horse.get_output_value("registration")}',
                callback=self.parse_pedigree,
                cb_kwargs=dict(horse=horse)
            )

        else:
            summary_years = []

            for summary_json in response_json['result']:
                summary_years.append(summary_json['year'])

                summary = ItemLoader(item=SummaryItem())

                summary.add_value('year', int(summary_json['year']))
                summary.add_value('starts', summary_json['numberOfStarts'])
                summary.add_value('wins', summary_json['numberOfFirstPlaces'])
                summary.add_value('seconds', summary_json['numberOfSecondPlaces'])
                summary.add_value('thirds', summary_json['numberOfThirdPlaces'])
                summary.add_value('mobile_mark', summary_json['autoRecord'])
                summary.add_value('standing_mark', summary_json['voltRecord'])
                summary.add_value('purse', summary_json['earnings'] / 100)

                horse.add_value('start_summary', summary.load_item())

            yield JsonRequest(
                url=f'{BASE_URL}/infopanel/starts/horse/{horse.get_output_value("registration")}/{summary_years[0]}-01-01/{summary_years[0]}-12-31',
                callback=self.parse_starts,
                cb_kwargs=dict(horse=horse, summary_years=summary_years)
            )


    def parse_starts(self, response, horse, summary_years):
        """
        Parse the racelines from the response, check if there is any yearly
        summaries left, if so get it and parse it else continue with the pedigree.
        """
        response_json = json.loads(response.body)

        for raceline_json in response_json['result']:
            if raceline_json['raceDayKey'] is None:
                continue

            raceline = ItemLoader(item=RacelineItem())

            raceline.add_value('date', raceline_json['raceDate'].split('T')[0])
            raceline.add_value('link', raceline_json['raceDayKey'])
            raceline.add_value('racetrack', raceline_json['sportTrackName'])
            raceline.add_value('racetrack_code', raceline_json['sportTrackCode'])
            raceline.add_value('racetype', raceline_json['odds'])
            raceline.add_value('driver', raceline_json['driverDisplayName'])
            raceline.add_value('racenumber', raceline_json['raceNumber'])
            raceline.add_value('postposition', raceline_json['postPosition'])
            raceline.add_value('startnumber', raceline_json['startNumber'])
            raceline.add_value('distance', raceline_json['distance'])
            raceline.add_value('monte', raceline_json['monte'])
            raceline.add_value('startmethod', raceline_json['startMethod'])
            raceline.add_value('started', raceline_json['kmTime'])

            if raceline.get_output_value('started'):
                raceline.add_value('finish', raceline_json['place'])
                raceline.add_value('racetime', raceline_json['kmTime'])
                raceline.add_value('gallop', raceline_json['galloped'])
                raceline.add_value('purse', raceline_json['prize'])
                raceline.add_value('ev_odds', raceline_json['odds'] if raceline_json['odds'].isnumeric() else None)
                raceline.add_value('disqualified', raceline_json['kmTime'])
                raceline.add_value('disqstring', raceline_json['kmTime'])

            horse.add_value('starts', raceline.load_item())

        summary_years.pop(0)

        if len(summary_years) == 0:
            yield JsonRequest(
                url=f'{BASE_URL}/infopanel/pedigree/{horse.get_output_value("registration")}',
                callback=self.parse_pedigree,
                cb_kwargs=dict(horse=horse)
            )

        else:
            yield JsonRequest(
                url=f'{BASE_URL}/infopanel/starts/horse/{horse.get_output_value("registration")}/{summary_years[0]}-01-01/{summary_years[0]}-12-31',
                callback=self.parse_starts,
                cb_kwargs=dict(horse=horse, summary_years=summary_years)
            )


    def parse_pedigree(self, response, horse):
        """
        Parse the pedigree then get the list for the horse's offspring.
        """
        response_json = json.loads(response.body)

        ancestors = []

        keys = ['father', 'mother', 'fathersFather', 'fathersMother', 'mothersFather', 'mothersMother',
                'fathersFathersFather', 'fathersFathersMother', 'fathersMothersFather', 'fathersMothersMother',
                'mothersFathersFather', 'mothersFathersMother', 'mothersMothersFather', 'mothersMothersMother']

        for key in keys:
            ancestor_json = response_json['result'][key]

            ancestor = ItemLoader(item=HorseItem())

            ancestor.add_value('name', ancestor_json['name'])
            ancestor.add_value('country', ancestor_json['name'])
            ancestor.add_value('sex', 'horse' if key.endswith('ather') else 'mare')
            ancestor.add_value('registration', ancestor_json['horseRegistrationNumber'])

            ancestors.append(ancestor)

        add_parents(ancestors[2], ancestors[6], ancestors[7])
        add_parents(ancestors[3], ancestors[8], ancestors[9])
        add_parents(ancestors[4], ancestors[10], ancestors[11])
        add_parents(ancestors[5], ancestors[12], ancestors[13])

        add_parents(ancestors[0], ancestors[2], ancestors[3])
        add_parents(ancestors[1], ancestors[4], ancestors[5])

        add_parents(horse, ancestors[0], ancestors[1])

        yield JsonRequest(
            url=f'{BASE_URL}/infopanel/offspring/{horse.get_output_value("registration")}',
            callback=self.parse_offspring,
            cb_kwargs=dict(horse=horse)
        )


    def parse_offspring(self, response, horse):
        """
        Parse the list of offspring the horse has. Skip offspring that are
        unregistered. If the horse is a mare and she has offspring that has not
        been retrieved, those will be collected.
        """
        response_json = json.loads(response.body)

        for offspring_json in response_json['result']:
            if offspring_json['certificationStatus'] == 'Makulert':
                continue

            offspring = ItemLoader(item=HorseItem())

            offspring.add_value('name', offspring_json['name'])
            offspring.add_value('country', offspring_json['name'])
            offspring.add_value('registration', offspring_json['horseRegistrationNumber'])
            offspring.add_value('sex', offspring_json['sex'])
            offspring.add_value('birthdate', f'{offspring_json["birthYear"]}-01-01')

            parent = ItemLoader(item=HorseItem())

            parent_sex = 'fa' if horse.get_output_value('sex') == 'mare' else 'mo'

            parent.add_value('name', offspring_json[f'{parent_sex}thersName'])
            parent.add_value('country', offspring_json[f'{parent_sex}thersName'])
            parent.add_value('registration', offspring_json[f'{parent_sex}thersHorseRegistrationNumber'])
            parent.add_value('sex', 'horse' if horse.get_output_value('sex') == 'mare' else 'mare')

            offspring.add_value('sire' if parent.get_output_value('sex') == 'horse' else 'dam', parent.load_item())

            if offspring_json['numberOfStarts'] != 0:
                summary = ItemLoader(item=SummaryItem())

                summary.add_value('starts', offspring_json['numberOfStarts'])
                summary.add_value('wins', offspring_json['numberOfFirstPlaces'])
                summary.add_value('seconds', offspring_json['numberOfSecondPlaces'])
                summary.add_value('thirds', offspring_json['numberOfThirdPlaces'])
                summary.add_value('mobile_mark', offspring_json['autoRecord'])
                summary.add_value('standing_mark', offspring_json['voltRecord'])
                summary.add_value('purse', offspring_json['earnings'] / 100)

                offspring.add_value('start_summary', summary.load_item())

            outfile = f'{offspring.get_output_value("registration").replace(" ", "_")}.json'

            if horse.get_output_value('sex') == 'mare' and not os.path.exists(os.path.join(JSON_DIRECTORY, 'horses', outfile)):
                yield JsonRequest(
                    url=f'{BASE_URL}/infopanel/liferow/horse/{offspring.get_output_value("registration")}',
                    callback=self.parse
                )

            horse.add_value('offspring', offspring.load_item())

        yield horse.load_item()
