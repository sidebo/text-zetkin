"""
This script sends text messages to activists using the Zetkin API and 46elks API
The name, and other fields of recipients may be accessed using placesholders like
{person.first_name} in the text.
"""
import sys
import requests
import phonenumbers
import re
import math
import yaml
from dateutil import parser, tz
from datetime import datetime

ZETKIN_BASE_URL = 'https://api.zetk.in/v1/'
TEXT_LIMIT = 160
PRICE_PER_TEXT = 0.35
VAT = 1.25
CURRENCY = 'SEK'

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

def zetkin_api_get(url, org_id, zetkin_access_token):
    base_url = ZETKIN_BASE_URL + 'orgs/' + org_id + '/'
    request_url = base_url + url
    try:
        headers = {'Authorization': 'Bearer ' + zetkin_access_token,
                   'Content-Type': 'application/json' }
        response = requests.get(request_url, headers=headers)
    except:
        raise Exception("ERROR: Cannot access Zetkin URL " + url)
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

def send_texts(people, text, choice, action=None):
    people = [person for person in people if person['phone'] is not None]

    print('\nSend to the following people: ')

    p = re.compile('\{[^\}]+\}')
    tokens = p.findall(text)
    tokens = [t.strip('{}').split('.') for t in tokens]

    over_limit_count = 0

    total_text_count = 0

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

    print("\nPlease reivew the %d people that you have chosen to text as part of the %s %s" % (len(people), option['title'], _type))
    print("Press enter when you want to move to the nex page")

    idx = 0
    PAGE_SIZE = 20
    while idx < len(texts):
        input("\nPress enter to continue\n")
        for text in texts[idx:idx+PAGE_SIZE]:
            print("%s, %s" % (text['name'], text['phone']))
        idx += PAGE_SIZE

    print(texts[0]['text'])
    print("\n\nHave you reviewed all the information and want to send this message? Type SEND, othewise type SKIP")
    send = ""
    while send not in ["SEND", "SKIP"]:
        send = input()

    if send == "SEND":
        with open('log.yaml', 'a') as log_file:
            for text in texts:
                log = send_sms(text['text'],text['phone'], SMS_USERNAME, SMS_PASSWORD, SMS_FROM)
                yaml.safe_dump(log, log_file)

with open(sys.argv[1], "rt") as f:
    lines = f.readlines()
    text = ''.join(lines)
    text = text.strip()

log = {}
zetkin_access_token = ''

if len(sys.argv) < 2:
    print("Usage: text.py file_with_text [org_id [access_token]]")

if len(sys.argv) > 2:
    org_id = sys.argv[2]
else:
    org_id = input("Please enter organization ID: ")
if len(sys.argv) > 3:
    zetkin_access_token = sys.argv[3]
else:
    zetkin_access_token = input("Please enter Zetkin access token: ")

SMS_USERNAME = input('Please enter 46elks API username: ')
SMS_PASSWORD = input('Please enter 46elks API password: ')
SMS_FROM = input("Please enter 46elks phone number")

print("Do you wish to text people who match a tag/query or people who participat in an action?")
choice = ''
while choice not in(['t','q','a']):
    choice = input("(t)ag/(q)uery/(a)ction: ")

if(choice == 't'):
    options = zetkin_api_get('people/tags', org_id, zetkin_access_token)
elif(choice == 'q'):
    options = zetkin_api_get('people/queries', org_id, zetkin_access_token)
elif(choice == 'a'):
    options = zetkin_api_get('campaigns', org_id, zetkin_access_token)

print("Choose from these options: ")
for idx, option in enumerate(options):
    print(str(idx) + ": " + option['title'])

option_idx = ''
while not option_idx.isdigit():
    option_idx = input("Which option? ")

option = options[int(option_idx)]

if choice == 's':
    people = zetkin_api_get('people/queries/%d/matches' % option['id'], org_id, zetkin_access_token)
    send_texts(people, text, choice)
elif choice == 't':
    people = zetkin_api_get('people/tags/%d/people' % option['id'], org_id, zetkin_access_token)
    send_texts(people, text, choice)
elif choice == 'a':
    today = datetime.now().strftime('%Y-%m-%d')
    campaign_actions = zetkin_api_get('campaigns/%d/actions?filter=start_time>%s>' % (option['id'], today), org_id, zetkin_access_token)

    # Filter any actions without contacts
    campagin_actions = [action for action in campaign_actions if action['contact']]

    for action in campaign_actions:
        action['start_time'] = parser.parse(action['start_time'])
        action['end_time'] = parser.parse(action['end_time'])

        contact = zetkin_api_get('people/%d' % action['contact']['id'], org_id, zetkin_access_token)

        # Format phone number
        phone = format_phone(contact['phone'])
        contact['phone'] = phone

        action['contact'] = contact

    print("Choose from actions to remind")
    for idx, action in enumerate(campagin_actions):
        print("%d: %s, %s, %s" % (idx,
                                  action['title'] if action['title'] else action['activity']['title'],
                                  action['location']['title'],
                                  action['start_time'].strftime('%Y-%m-%d %H:%M')))

    action_choice = input('Which action? (ALL for all)')
    if(action_choice == "ALL"):
        for action in campaign_actions:
            people = zetkin_api_get('actions/%d/participants' % action['id'], org_id, zetkin_access_token)
            send_texts(people, text, choice, action)
    else:
        action = campaign_actions[int(action_choice)]
        people = zetkin_api_get('actions/%d/participants' % action['id'], org_id, zetkin_access_token)
        send_texts(people, text, choice, action)
