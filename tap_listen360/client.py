import singer
import requests
import time
from requests.auth import HTTPBasicAuth

LOGGER = singer.get_logger()


class BaseClient:
    RATE_LIMIT_PAUSE = 30
    url = None
    auth_type = None

    def __init__(self, config):
        self.config = config

    @staticmethod
    def requests_method(method, request_config, body):
        # if 'Content-Type' not in request_config['headers']:
        #     request_config['headers']['Content-Type'] = 'application/json'

        return requests.request(
            method,
            request_config['url'],
            headers=request_config['headers'],
            params=request_config['params'],
            json=body,
            auth=HTTPBasicAuth(request_config['api_key'], '')
            )

    def make_request(self, request_config, body=None, method='GET'):
        retries = 5
        delay = 30
        backoff = 1.5
        attempt = 1
        while retries >= attempt:
            LOGGER.info("Making {} request to {}".format(
                method, request_config['url']))

            with singer.metrics.Timer('request_duration', {}) as timer:
                response = self.requests_method(method, request_config, body)

            if response.status_code in [429, 503, 504]:
                LOGGER.info(f"[Error {response.status_code}] with this "
                            f"response:\n {response}")
                time.sleep(delay)
                delay *= backoff
                attempt += 1
            else:
                return response

        logger.info(f"Reached maximum retries ({retries}), failing...")
        raise ValueError("Maximum retries reached")
