# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
from finland.items import RacedayItem, HorseItem

import json
import os

# from horses.db.connect import DB
# from horses.horses.horse import insert_pedigree, insert_horse, insert_offspring, insert_result_summary, find_organisation

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/finland'
ORGANISATION = 'Suomen Hippos'

class FinlandPipeline(object):

    def process_item(self, item, spider):
        if isinstance(item, RacedayItem):
            if item['status'] == 'cancelled':
                filename    = '_'.join([item['date'].replace('-', '_'), item['racetrack'].lower().replace(', ', '_')]) + '.json'
            else:
                filename    = '_'.join([item['date'].replace('-', '_'), item['racetrack_code'].lower()]) + '.json'
            outfile     = os.path.join(JSON_DIRECTORY, item['status'] if item['status'] != 'cancelled' else 'result', filename)
            json.dump(dict(item),
                      open(outfile, 'w'),
                      indent = 4
                      )
            return filename

        elif isinstance(item, HorseItem):
            filename    = item['link'] + '.json'
            outfile     = os.path.join(JSON_DIRECTORY, 'horses', filename)
            json.dump(dict(item),
                      open(outfile, 'w'),
                      indent = 4
                      )
            return filename


# class DBPipeline(object):
#     def open_spider(self, spider):
#         self.db = DB().connect()
#
#         self.organisation = find_organisation(self.db, ORGANISATION)
#
#     def close_spider(self, spider):
#         self.db.close()
#
#     def process_item(self, item, spider):
#         if isinstance(item, HorseItem):
#             horse = insert_pedigree(self.db, self.organisation, item)
#
#             if item.get('offspring'):
#                 insert_offspring(self.db, self.organisation, item['offspring'], horse)
#
#             if item.get('start_summary'):
#                 insert_result_summary(self.db, self.organisation, item['start_summary'], horse)
#
#         return item
