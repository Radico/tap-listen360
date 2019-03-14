from tap_kit import TapExecutor
from tap_kit.utils import timestamp_to_iso8601
from singer.catalog import Catalog, CatalogEntry
from tap_kit.utils import (transform_write_and_count, format_last_updated_for_request)
from xml.etree import ElementTree
import xmltodict


import json
import time
import pendulum
import singer
import sys
import datetime
import pytz
from datetime import timedelta

LOGGER = singer.get_logger()


class Listen360Executor(TapExecutor):
    """
    """

    def __init__(self, streams, args, client):
        """
        """
        super(Listen360Executor, self).__init__(streams, args, client)

        self.replication_key_format = 'timestamp'
        self.api_key = self.client.config['api_key']
        self.url = 'https://app.listen360.com/organizations/1688179941532767233/'

    def call_incremental_stream(self, stream):
        """
        Method to call all incremental synced streams
        """
        last_updated = format_last_updated_for_request(
            stream.update_and_return_bookmark(), self.replication_key_format)

        request_config = {
            'url': self.generate_api_url(stream),
            'headers': self.build_headers(),
            'params': self.build_initial_params(stream, last_updated),
            'run': True,
            'api_key': self.api_key
        }
        
        LOGGER.info("Extracting %s since %s" % (stream, last_updated))
        self.total_contacts = 0

        while request_config['run']:

            LOGGER.info("Params: %s" % (request_config['params']))
            res = self.client.make_request(request_config)

            if res.status_code != 200:
                raise AttributeError('Received status code {}'.format(res.status_code))
    
            root = ElementTree.fromstring(res.text)
            records = []
            for child in root:
                xml_dict = {}
                for grandchild in child:
                    xml_dict[grandchild.tag] = grandchild.text
                records.append(xml_dict)


            self.total_contacts += len(records)
            LOGGER.info('Total Records is {}'.format(self.total_contacts))


            if self.should_write(records, stream, last_updated):
                transform_write_and_count(stream, records)
            
            # last_updated = self.get_lastest_update(
            #     records,
            #     last_updated
            # )

            stream.update_bookmark(last_updated)

            request_config = self.update_for_next_call(
                res,
                request_config,
                stream,
                records
            )

        formated_update = self.format_updated(request_config['params']['updated_before'])
        LOGGER.info('setting last updated to {}'.format(formated_update))
        return formated_update

    def generate_api_url(self, stream):
        return self.url + stream.stream + '.xml'

    def format_updated(self, updated_before):
        date = datetime.datetime.strptime(updated_before, '%Y-%m-%d') - timedelta(days=1)
        return date.strftime('%Y-%m-%dT%H:%M:%S%z')

    def build_initial_params(self, stream, last_updated=None):
        low_window, high_window = self.get_low_and_high_window(last_updated)

        return {
            'page': 1,
            'updated_before': self.format_last_modified(high_window),
            'updated_after': self.format_last_modified(low_window)
        }
    
    def get_low_and_high_window(self, last_updated):

        if type(last_updated) == str:
            date = datetime.datetime.strptime(last_updated, '%Y-%m-%dT%H:%M:%S%z')
            last_updated = int(date.timestamp())
        
        LOGGER.info('Last Updated is: {}'.format(last_updated))
        low_window = last_updated
        if last_updated >= 0 and last_updated < 1517443200:
            high_window = 1517443200
        elif last_updated >= 1517443200:
            # 1 month windows
            high_window = last_updated + (30 * 24 * 60 * 60)

        if high_window > int(time.time()):
            high_window = int(time.time())

        return low_window, high_window        

    def update_for_next_call(self, res, request_config, stream, records):
        
        if len(records) == 0:
            return {
                "url": self.url,
                "headers": request_config["headers"],
                "params": request_config['params'],
                "run": False,
            }

        return {
            "url": self.generate_api_url(stream),
            "headers": request_config["headers"],
            "params": self.build_next_params(request_config['params']),
            "run": True,
            "api_key": self.api_key
        }

    def format_last_modified(self, last_updated):
        date = datetime.datetime.fromtimestamp(last_updated, tz=pytz.UTC)
        last_mod = '{}'.format(date.strftime('%Y-%m-%d'))
        return last_mod

    def build_next_params(self, params):
        params['page'] += 1
        return params

