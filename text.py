"""
This script sends text messages to activists using the Zetkin API and 46elks API
The name, and other fields of recipients may be accessed using placesholders like
{person.first_name} in the text.
"""
import sys
import os
import requests
import phonenumbers
import re
import math
import yaml
import binascii
import subprocess
import time
import pickle
import jwt
from datetime import datetime
from selenium import webdriver
from dotenv import load_dotenv
from dateutil import parser, tz
from datetime import datetime

ZETKIN_BASE_URL = 'https://api.zetk.in/v1/'
TEXT_LIMIT = 160
PRICE_PER_TEXT = 0.35
VAT = 1.25
CURRENCY = 'SEK'

people_by_phone = None

# Load environment variables from .env
load_dotenv()

def normalize_phone(phone, country='SE'):
    if phone is None:
        return None

    try:
        phone = phonenumbers.parse(phone, country)
        phone = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)
    except: # Not a number
        return None

    # Only allow +467 (Swedish mobile phone) numbers
    if phone[0:4] != '+467':
        return None
    return phone

def format_phone(phone, country='SE'):
    if phone is None:
        return None

    try:
        phone = phonenumbers.parse(phone, country)
    except: # Not a number
        return None

    return phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.NATIONAL)

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

def zetkin_api_get(url, org_id, zetkin_access_token):
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

def send_sms(text, phone, username, password, from_number):
    print("Send SMS to %s: %s" % (phone, text))
    resp = requests.post(
        "https://api.46elks.com/a1/sms",
        auth = (username, password),
        data = {
            "from": from_number,
            "to": phone,
            "message": text,
        }
    )
    return {
        'phone': phone,
        'text': text,
        'response': {
            'status': resp.status_code,
            'body': resp.text,
        },
    }

def sms_get_replies(username, password, phone, limit=50):
    try:
        response = requests.get(
            "https://api.46elks.com/a1/sms",
            auth = (username, password),
            params = {
                "limit": limit,
                "account": "me",
                "to": phone,
                "status": "",
            }
        )
    except:
        raise Exception("ERROR: Cannot fetch texts from 46Elks")

    result = response.json()
    return result['data']

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


def send_texts(people, text, choice, action=None):
    people = [person for person in people if person['phone'] is not None]

    if not text:
        text = edit_text_file()

    print('\nSend to the following people: ')

    (texts, over_limit_count, total_text_count) = prepare_texts(text, people, action)

    print("%d/%d texts over the text limit!" % (over_limit_count, len(people)))

    print("This will cost %.2f %s" % (total_text_count*PRICE_PER_TEXT*VAT, CURRENCY))

    print("Please review the first text:\n")
    print("Recipient: %s" % texts[0]['phone'])
    print(texts[0]['text'])

    _type = ''
    if choice == 't':
        _type = 'tag'
    elif choice == 'q':
        _type = 'query'
    elif choice == 'a':
        _type = 'action'
    elif choice == 'r':
        _type = 'response'

    if choice != 'r':
        print("\nPlease reivew the %d people that you have chosen to text as part of the %s" % (len(people), _type))
        print("Press enter when you want to move to the nex page")

        idx = 0
        PAGE_SIZE = 20
        while idx < len(texts):
            input("\nPress enter to continue\n")
            for text in texts[idx:idx+PAGE_SIZE]:
                print("%s, %s" % (text['name'], text['phone']))
            idx += PAGE_SIZE

        print(texts[0]['text'])

    print("\n\nHave you reviewed all the information and want to send this message? Type SEND, othewise type SKIP. If you're not satisfied with text, type EDIT")
    send = ""
    while send not in ["SEND", "SKIP"]:
        if send == "EDIT":
            text = edit_text_file()
            (texts, over_limit_count, total_text_count) = prepare_texts(text, people)
            print("Please review the first text:\n")
            print("Recipient: %s" % texts[0]['phone'])
            print(texts[0]['text'])

            print("%d/%d texts over the text limit!" % (over_limit_count, len(people)))

            print("This will cost %.2f %s" % (total_text_count*PRICE_PER_TEXT*VAT, CURRENCY))

        send = input()

    if send == "SEND":
        with open('log.yaml', 'a') as log_file:
            for text in texts:
                log = send_sms(text['text'],text['phone'], SMS_USERNAME, SMS_PASSWORD, SMS_FROM)
                yaml.safe_dump(log, log_file)

def read_text_file(filename):
    with open(filename, "rt") as f:
        lines = f.readlines()
        text = ''.join(lines)
        text = text.strip()
    return text

def edit_text_file():
    filename = binascii.b2a_hex(os.urandom(15))
    p = subprocess.Popen(('gedit', filename))
    p.wait()
    return read_text_file(filename)

def get_option(type, value):
    if type == 'r':
        return (value['from']) + ' ' + get_person_name(value['from']) +  ': '  + value['message'] + ' (' + value['created'] + ')'
    else:
        return value['title']

def get_people_by_phone(people):
    people_by_phone = {}

    for person in people:
        intl_phone = normalize_phone(person['phone'])
        people_by_phone[intl_phone] = person

    return people_by_phone

def get_person_name(phone):
    person = people_by_phone.get(phone)
    first_name = person['first_name'] if person else 'Unknown'
    last_name = person['last_name'] if person else 'Unknown'

    return first_name + ' ' + last_name

def print_phone_history(message):
    texts = sms_get_replies(SMS_USERNAME, SMS_PASSWORD, phone, 1)
    print("Text history with " + phone + ": ")
    for text in texts:
        print(text['from'] + ': ' + text['message']  + ' (' + text['created'] + ')')

    print(message['from'] + ': ' + message['message'] + ' (' + message['created'] + ')')

text = None
if len(sys.argv) > 1:
    text = read_text_file(sys.argv[1])

log = {}
zetkin_access_token = ''

if len(sys.argv) < 2:
    print("Usage: text.py file_with_text [org_id [access_token]]")

if len(sys.argv) > 2:
    org_id = sys.argv[2]
else:
    org_id = os.environ.get('ZETKIN_ORG') or input("Please enter organization ID: ")
if len(sys.argv) > 3:
    zetkin_access_token = sys.argv[3]
else:
    zetkin_access_token = get_access_token()

try:
    data_cache = open(".data-cache-%s" % org_id, 'rb')
    CACHE = pickle.load(data_cache)
    data_cache.close()
except Exception as e:
    print(e)
    CACHE = {}


SMS_USERNAME = os.environ.get('46ELKS_API_USER') or input('Please enter 46elks API username: ')
SMS_PASSWORD = os.environ.get('46ELKS_API_PASSWORD') or input('Please enter 46elks API password: ')
SMS_FROM = os.environ.get('46ELKS_PHONE') or input("Please enter 46elks phone number: ")

continue_texting = 'R'
while continue_texting == 'R':
    print("Do you wish to text people who match a tag/query or people who participat in an action?")
    choice = ''
    while choice not in(['t','q','a','r']):
        choice = input("(t)ag/(q)uery/(a)ction/(r)esponse: ")

    if(choice == 't'):
        options = zetkin_api_get('people/tags', org_id, zetkin_access_token)
    elif(choice == 'q'):
        options = zetkin_api_get('people/queries', org_id, zetkin_access_token)
    elif(choice == 'a'):
        options = zetkin_api_get('campaigns', org_id, zetkin_access_token)
    elif(choice == 'r'):
        people = zetkin_api_get('people', org_id, zetkin_access_token)
        if people_by_phone is None:
            people_by_phone = get_people_by_phone(people)
        options = sms_get_replies(SMS_USERNAME, SMS_PASSWORD, SMS_FROM)

    print("Choose from these options: ")
    for idx, option in enumerate(options):
        print(str(idx) + ": " + get_option(choice, option))

    option_idx = ''
    while not option_idx.isdigit():
        option_idx = input("Which option? ")

    option = options[int(option_idx)]


    if choice == 'q':
        people = zetkin_api_get('people/queries/%d/matches' % option['id'], org_id, zetkin_access_token)
        if text is None:
            text = edit_text_file()
        send_texts(people, text, choice)
    elif choice == 't':
        people = zetkin_api_get('people/tags/%d/people' % option['id'], org_id, zetkin_access_token)
        if text is None:
            text = edit_text_file()
        send_texts(people, text, choice)
    elif choice == 'r':
        phone = option['from']
        print_phone_history(option)
        send_texts([{
            'phone': phone,
            'first_name': '',
            'last_name': '',
        }], text, choice)
    elif choice == 'a':
        today = datetime.now().strftime('%Y-%m-%d')
        campaign_actions = zetkin_api_get('campaigns/%d/actions?filter=start_time>%s>' % (option['id'], today), org_id, zetkin_access_token)

        # Filter any actions without contacts
        campaign_actions = [action for action in campaign_actions if action['contact']]

        for action in campaign_actions:
            action['start_time'] = parser.parse(action['start_time'])
            action['end_time'] = parser.parse(action['end_time'])

            # If not contact has been assigned, skip the action
            if not action['contact']:
                continue

            contact = zetkin_api_get('people/%d' % action['contact']['id'], org_id, zetkin_access_token)

            # Format phone number
            phone = format_phone(contact['phone'])
            contact['phone'] = phone

            action['contact'] = contact

        print("Choose from actions to remind")
        for idx, action in enumerate(campaign_actions):
            print("%d: %s, %s, %s" % (idx,
                                      action['title'] if action['title'] else action['activity']['title'],
                                      action['location']['title'],
                                      action['start_time'].strftime('%Y-%m-%d %H:%M')))

        action_choice = input('Which action(s)? (comma-separated, ALL for all)')
        
        campaign_actions = campaign_actions if action_choice == "ALL" else \
            [campaign_actions[idx] for idx in [int(ac.strip()) for ac in action_choice.split(",")]]
        
        for action in campaign_actions:
            people = zetkin_api_get('actions/%d/participants' % action['id'], org_id, zetkin_access_token)
            send_texts(people, text, choice, action)

    continue_texting = ""
    while continue_texting not in ['R', 'EXIT']:
        print('Do you want to text more? Type R, otherwise, type EXIT')
        continue_texting = input()
