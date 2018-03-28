import calendar
import datetime as dt
import os

from google.cloud import datastore


def is_production():
    return os.environ.get('ENVIRONMENT') == 'production'


def get_start_time():
    date = get('first_day')
    year, month, day = date.split('/')
    return dt.datetime.utcfromtimestamp(calendar.timegm((int(year), int(month), int(day), 0, 0, 0)))


def get(setting):
    result = os.environ.get(setting.upper())

    if result:
        return result

    client = datastore.Client()
    query = client.query(kind='Setting')
    query.add_filter('name', '=', setting.lower())
    result = list(query.fetch(1))
    if result:
        return result[0].get('value')
