from selenium import webdriver
import pickle
import time
import jwt
import math
from datetime import datetime
import requests
import re
from sms import normalize_phone

TEXT_LIMIT = 160
PRICE_PER_TEXT = 0.35
VAT = 1.25
CURRENCY = 'SEK'


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

def prepare_texts(text, people, action=None):
    over_limit_count = 0

    total_text_count = 0

    p = re.compile('\{[^\}]+\}')
    tokens = p.findall(text)
    tokens = [t.strip('{}').split('.') for t in tokens]

    texts = []

    for person in people:
        phone = normalize_phone(person['phone'])
        if phone is None:
            continue
        person_text = text
        for t in tokens:
            value = ''
            if t[0] == 'person':
                value = person[t[1]]
            elif t[0] == 'action':
                if action is None:
                    raise Exception('action variables not recognized for this type')
                if t[1] == 'start_time':
                    value = action['start_time'].strftime('%H:%M')
                elif t[1] == 'location':
                    value = action['location']['title']
                elif t[1] == 'contact':
                    value = action['contact'][t[2]]
                else:
                    value = action[t[1]]
            else:
                raise Exception('%s is not a recognized type' % t[0])
            person_text = person_text.replace('{' + '.'.join(t) + '}', value)

        if len(person_text) > TEXT_LIMIT:
            over_limit_count += 1
            total_text_count += math.ceil(len(person_text)/TEXT_LIMIT)
        else:
            total_text_count += 1

        texts.append({
            'text': person_text,
            'phone': phone,
            'name': person['first_name'] + ' ' + person['last_name'],
        })
    return (texts, over_limit_count, total_text_count)

def get_people_by_phone(people):
    people_by_phone = {}
    
    for person in people:
        intl_phone = normalize_phone(person['phone'])
        people_by_phone[intl_phone] = person

    return people_by_phone

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


def zetkin_api_get(url, org_id, zetkin_access_token, CACHE) -> dict:
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
