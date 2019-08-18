import json
import csv
import codecs
from logging import getLogger
from os.path import join, exists
from re import search, sub
from datetime import date
from requests import session

log = getLogger(__name__)

class GarminConnect:

    # lean Python 3 script to export Garmin actitvities to JSON or CSV file
    # based on code from Andre Cooke (https://github.com/andrewcooke) https://github.com/andrewcooke/choochoo/blob/master/ch2/fit/download/connect.py
    # logic and data from https://github.com/tcgoetz/GarminDB/blob/master/download_garmin.py
    # updated to the recent Garmin API specification
    # added features to export JSON and CSV
    # 2019-08-18

    base_url = 'https://connect.garmin.com'
    sso_url = 'https://sso.garmin.com/sso'
    modern = base_url + '/modern'
    signin = sso_url + '/signin'
    daily = modern + '/proxy/activitylist-service/activities/search/activities' # updated to the recent Garmin API specification

    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; https://github.com/andrewcooke/choochoo)',
        'origin': 'https://sso.garmin.com'
    }

    def __init__(self, log_response=False):
        self._r = session()
        self._log_response = log_response

    def login(self, username, password):

        log.info('Connecting to Garmin Connect as %s' % username)

        params = {
            'webhost': self.base_url,
            'service': self.modern,
            'source': self.signin,
            'redirectAfterAccountLoginUrl': self.modern,
            'redirectAfterAccountCreationUrl': self.modern,
            'gauthHost': self.sso_url,
            'locale': 'en_US',
            'id': 'gauth-widget',
            'cssUrl': 'https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css',
            'clientId': 'GarminConnect',
            'rememberMeShown': 'true',
            'rememberMeChecked': 'false',
            'createAccountShown': 'true',
            'openCreateAccount': 'false',
            'usernameShown': 'false',
            'displayNameShown': 'false',
            'consumeServiceTicket': 'false',
            'initialFocus': 'true',
            'embedWidget': 'false',
            'generateExtraServiceTicket': 'false'
        }

        response = self._log_r(self._r.get(self.signin, headers=self.headers, params=params))
        response.raise_for_status()

        data = {
            'username': username,
            'password': password,
            'embed': 'true',
            'lt': 'e1s1',
            '_eventId': 'submit',
            'displayNameRequired': 'false'
        }

        response = self._log_r(self._r.post(self.signin, headers=self.headers, params=params, data=data))
        response.raise_for_status()

        response_url = search(r'"(https:[^"]+?ticket=[^"]+)"', response.text)
        if not response_url:
            log.debug(response.text)
            raise Exception('Could not find response URL')
        response_url = sub(r'\\', '', response_url.group(1))
        log.debug('Response URL: %s' % response_url)

        response = self._log_r(self._r.get(response_url))
        response.raise_for_status()

    def _log_r(self, response):
        if self._log_response:
            log.debug('headers: %s' % response.headers)
            log.debug('reason: %s' % response.reason)
            log.debug('cookies: %s' % response.cookies)
            log.debug('history: %s' % response.history)
        return response

    def get_monitoring_date(self, start_date, end_date): # retrieve activities from start_date to end_date as total numbers of items retrieved is limited by Garmin
        response = self._log_r(self._r.get(self.daily + '?' + 'startDate=' + start_date + '&' + 'endDate=' + end_date, headers=self.headers))
        print('Retrieving json data stream from ' + self.daily + '?' + 'startDate=' + start_date + '&' + 'endDate=' + end_date)
        response.raise_for_status()
        return response

    def write_csv(self, json_data, filename): # CSV writer
        with codecs.open(filename, 'w+', encoding='utf-8') as outf:
            writer = csv.DictWriter(outf, json_data[0].keys())
            writer.writeheader()
            for row in json_data:
                writer.writerow(row)

    def write_json(self, json_data, filename): # JSON writer
        with codecs.open(filename, 'w+', encoding='utf-8') as json_file:
            json.dump(json_data, json_file)

    def get_monitoring_to_json_file_date(self, start_date, end_date, dir):
        f = join(dir, start_date + '_to_' + end_date + '.json')
        response = self.get_monitoring_date(start_date, end_date)
        j = json.loads(response.content)
        self.write_json(j, f)

    def get_monitoring_to_csv_file_date(self, start_date, end_date, dir):
        f = join(dir, start_date + '_to_' + end_date + '.csv')
        response = self.get_monitoring_date(start_date, end_date)
        j = json.loads(response.content)
        self.write_csv(j, f)


g = GarminConnect()
g.login('youruser', 'yourpassword')
g.get_monitoring_to_json_file_date('2018-01-1', '2018-12-31', 'yourpath')
