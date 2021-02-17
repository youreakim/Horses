from belgium.items import HorseItem, RacedayItem

import json
import os

JSON_DIRECTORY = '/home/youreakim/dokument/hastar/standardbred/json/scrapy/belgium'
ORGANISATION = 'Fédération Belge des Courses Hippiques'


class BelgiumPipeline(object):
    def process_item(self, item, spider):
        if isinstance(item, RacedayItem):
            filename = '_'.join([item['date'].replace('-', '_'),
                                    item['racetrack'].lower()]) + '.json'
            outfile = os.path.join(JSON_DIRECTORY, item['status'], filename)
            json.dump(dict(item),
                      open(outfile, 'w'),
                      indent = 4
                      )
            return filename

        elif isinstance(item, HorseItem):
            filename = item['link'] + '.json'
            outfile = os.path.join(JSON_DIRECTORY, 'horses', filename)
            json.dump(dict(item),
                      open(outfile, 'w'),
                      indent = 4
                      )
            return filename
