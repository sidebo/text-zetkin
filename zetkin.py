from selenium import webdriver
import pickle
import time
import jwt
from datetime import datetime
import requests
import os

ZETKIN_BASE_URL = 'https://api.zetk.in/v1/'

PEOPLE_BY_PHONE = None

def get_person_name(phone):
    person = PEOPLE_BY_PHONE.get(phone)
    first_name = person['first_name'] if person else 'Unknown'
    last_name = person['last_name'] if person else 'Unknown'

    return first_name + ' ' + last_name

def get_option(type, value):
    if type == 'r':
        return (value['from']) + ' ' + get_person_name(value['from']) +  ': '  + value['message'] + ' (' + value['created'] + ')'
    else:
        return value['title']

def get_access_token():
    browser = webdriver.Firefox()
    cookies = None
    try:
        cache = open('.api-cache', 'rb')
        cookies = pickle.load(cache)
        browser.get('https://organize.zetk.in/static/')
        for co in cookies:
            browser.add_cookie(co)
    except Exception as e:
        print(e)

    browser.get('https://organize.zetk.in')
    while True:
        time.sleep(1)
        cookies = browser.get_cookies()
        for co in cookies:
            if co['name'] == 'apiAccessToken':
                cache = open('.api-cache', 'wb+')
                pickle.dump(cookies, cache)
                cache.close()
                decoded = jwt.decode(co['value'], options={"verify_signature": False})
                issued_at = datetime.fromtimestamp(decoded['iat'])
                since_issued = datetime.now() - issued_at
                if since_issued.seconds < 3600:
                    browser.quit()
                    return co['value']
                else:
                    browser.get('https://organize.zetk.in')


def zetkin_api_get(url, org_id, zetkin_access_token, CACHE):
    if url in CACHE:
        response = CACHE[url]
    else:
        base_url = ZETKIN_BASE_URL + 'orgs/' + org_id + '/'
        request_url = base_url + url
        try:
            headers = {'Authorization': 'Bearer ' + zetkin_access_token,
                       'Content-Type': 'application/json' }
            response = requests.get(request_url, headers=headers)
            CACHE[url] = response
        except:
            raise Exception("ERROR: Cannot access Zetkin URL " + url)

        if url == 'people':
            data_cache = open(".data-cache-%s" % org_id, 'wb+')
            pickle.dump(CACHE, data_cache)
            data_cache.close()

    try:
        result = response.json()
        return result['data']
    except:
        raise Exception("ERROR: Cannot interpret response from " + url)
