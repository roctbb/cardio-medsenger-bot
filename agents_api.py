from config import *
import requests


def get_categories():
    data = {
        "api_key": APP_KEY,
    }

    try:
        result = requests.post(MAIN_HOST + '/api/agents/records/categories', json=data)
        return result.json()
    except Exception as e:
        print('connection error', e)
        return {}


def get_available_categories(contract_id):
    data = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
    }

    try:
        result = requests.post(MAIN_HOST + '/api/agents/records/available_categories', json=data)
        return result.json()
    except Exception as e:
        print('connection error', e)
        return {}


def get_records(contract_id, category_name, time_from=None, time_to=None, limit=None, offset=None):
    data = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "category_name": category_name,
    }

    if limit:
        data['limit'] = limit
    if offset:
        data['offset'] = offset
    if time_from:
        data['from'] = time_from
    if time_to:
        data['to'] = time_to

    try:
        result = requests.post(MAIN_HOST + '/api/agents/records/get', json=data)
        return result.json()
    except Exception as e:
        print('connection error', e)
        return {}


def add_record(contract_id, category_name, value, record_time=None):
    data = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "category_name": category_name,
        "value": value,
    }

    if record_time:
        data['time'] = record_time

    try:
        requests.post(MAIN_HOST + '/api/agents/records/add', json=data)
    except Exception as e:
        print('connection error', e)


def add_records(contract_id, values, record_time=None):
    data = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
    }

    if record_time:
        data['values'] = [{"category_name": category_name, "value": value, "time": record_time} for
                          (category_name, value) in values]
    else:
        data['values'] = [{"category_name": category_name, "value": value} for (category_name, value) in values]
    print(data)
    try:
        requests.post(MAIN_HOST + '/api/agents/records/add', json=data)
    except Exception as e:
        print('connection error', e)
