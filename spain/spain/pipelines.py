# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
from spain.items import RacedayItem, HorseItem

import json
import os

JSON_DIRECTORY              = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/spain'

class SpainPipeline(object):
    def process_item(self, item, spider):
        if isinstance(item, RacedayItem):
            filename    = '_'.join([item['date'].replace('-', '_'), item['racetrack'].replace(' ', '_').lower()]) + '.json'
            outfile     = os.path.join(JSON_DIRECTORY, item['status'], filename)
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
