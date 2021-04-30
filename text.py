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

def send_sms(text, phone, username, password):
    print("Send SMS to %s: %s" % (phone, text))
    resp = requests.post(
        "https://api.46elks.com/a1/sms",
        auth = (username, password),
        data = {
            "from": "+46766869576",
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
    org_id = input("Skriv in ditt organisations-ID: ")
if len(sys.argv) > 3:
    zetkin_access_token = sys.argv[3]
else:
    zetkin_access_token = input("Skriv in din Zetkin access token: ")

SMS_USERNAME = input('Please enter 46elks API username')
SMS_PASSWORD = input('Please enter 46elks API password')

print("Vill du skicka SMS till personer med en viss tagg eller personer som matchar en smart sökning?")
choice = ''
while choice not in(['t','s']):
    choice = input("(t)agg/(s)ökning: ")

if(choice == 't'):
    options = zetkin_api_get('people/tags', org_id, zetkin_access_token)
elif(choice == 's'):
    options = zetkin_api_get('people/queries', org_id, zetkin_access_token)

print("Choose from these options: ")
for idx, option in enumerate(options):
    print(str(idx) + ": " + option['title'])

option_idx = ''
while not option_idx.isdigit():
    option_idx = input("Which option? ")

option = options[int(option_idx)]

if choice == 's':
    people = zetkin_api_get('people/queries/%d/matches' % option['id'], org_id, zetkin_access_token)
elif choice == 't':
    people = zetkin_api_get('people/tags/%d/people' % option['id'], org_id, zetkin_access_token)

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
        else:
            raise Error('%s is not a recognized type' % t[0])
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

print("This will cost %d %s" % (total_text_count*PRICE_PER_TEXT*VAT, CURRENCY))

print("Please review the first text:\n")
print("Recipient: %s" % texts[0]['phone'])
print(texts[0]['text'])

if choice == 't':
    type = 'tag'
elif choice == 'q':
    type = 'query'

print("\nPlease reivew the %d people that you have chosen to text as part of the %s %s" % (len(people), option['title'], type))
print("Press enter when you want to move to the nex page")

idx = 0
PAGE_SIZE = 20
while idx < len(texts):
    input("\nPress enter to continue\n")
    for text in texts[idx:idx+PAGE_SIZE]:
        print("%s, %s" % (text['name'], text['phone']))
    idx += PAGE_SIZE


print(texts[0]['text'])
print("\n")
print("\n\nHave you reviewed all the information and want to send this message? Type SEND")
send = ""
while send != "SEND":
    send = input()

with open('log.yaml', 'w') as log_file:
    for text in texts:
        log = send_sms(text['text'],text['phone'], SMS_USERNAME, SMS_PASSWORD)
        yaml.safe_dump(log, log_file)
