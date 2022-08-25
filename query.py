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
import json
import pprint
from dotenv import load_dotenv
from dateutil import parser, tz
from datetime import datetime

ZETKIN_BASE_URL = 'https://api.zetk.in/v1/'

# Load environment variables from .env
load_dotenv()

def zetkin_api_get(url, org_id, zetkin_access_token):
    base_url = ZETKIN_BASE_URL + 'orgs/' + str(org_id) + '/'
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

def zetkin_api_post(url, org_id, zetkin_access_token, data):
    base_url = ZETKIN_BASE_URL + 'orgs/' + str(org_id) + '/'
    request_url = base_url + url
    try:
        headers = {'Authorization': 'Bearer ' + zetkin_access_token,
                   'Content-Type': 'application/json' }
        response = requests.post(request_url, headers=headers, json=data)
    except:
        raise Exception("ERROR: Cannot access Zetkin URL " + url)
    try:
        result = response.json()
        return result['data']
    except:
        raise Exception("ERROR: Cannot interpret response from " + url)

zetkin_access_token = ''

org_id = os.environ.get('ZETKIN_ORG') or input("Please enter organization ID: ")

if len(sys.argv) > 3:
    zetkin_access_token = sys.argv[3]
else:
    zetkin_access_token = input("Please enter Zetkin access token: ")

choice = ""
while choice not in ('a', 's'):
    choice = input("Activity history (a) or survey responses (s)")

if choice == 's':
    surveys = zetkin_api_get('surveys?recursive', org_id, zetkin_access_token)
    surveys = surveys
    for s in surveys:
        oid = s['organization']['id']
        sid = s['id']
        survey = zetkin_api_get('surveys/' + str(sid), oid, zetkin_access_token)
        s['elements'] = survey['elements']

    search_terms = [s.strip() for s in input("Enter search terms, separated by comma: ").split(',')]

    matching_options = []
    for s in surveys:
        for e in s['elements']:
            if e['type'] == 'question' and e['question']['response_type'] == 'options':
                question = e['question']
                for option in question['options']:
                    added = False
                    for search_term in search_terms:
                        if search_term.lower() in option['text'].lower() and added is False:
                            added = True
                            matching_options.append({
                                'survey': s['id'],
                                'question': e['id'],
                                'option': option['id'],
                                'option_text': option['text'],
                                'question_text': question['question'],
                                'organization': s['organization'],
                                'survey_title': s['title']
                            })

    selected_options = []
    for m in matching_options:
        print('In survey "' + m['survey_title'] +'" from "' + m['organization']['title'] + '"')
        print('Question: ' + m['question_text'])
        print('Option: ' + m['option_text'])
        include = ''
        while include not in ('y', 'Y', 'n', 'N'):
            include = input('Include? (y/n)')
        if include == 'y' or include == 'Y':
            selected_options.append(m)

    correct = ''
    while correct not in ('y', 'Y', 'n', 'N'):
        correct = input("Is this correct? (y/n)")

    if correct == 'y' or correct == 'Y':
        title = input('Title for your new query: ')

        filter_spec = [
            {
                'config': {
                    'operator': 'any',
                    'survey': s['survey'],
                    'question': s['question'],
                    'options': [s['option']],
                    'organizations': 'all',
                },
                'op': 'add',
                'type': 'survey_option',
            } for s in selected_options
        ]

        data = {
            'title': title,
            'org_access': 'suborgs',
            'filter_spec': filter_spec,
        }

        zetkin_api_post('people/queries', org_id, zetkin_access_token, data)

elif choice == 'a':
    activities = zetkin_api_get('activities?recursive', org_id, zetkin_access_token)

    search_terms = [s.strip() for s in input("Enter search terms, separated by comma: ").split(',')]

    matching_options = []
    for a in activities:
        for search_term in search_terms:
            if search_term.lower() in a['title'].lower():
                matching_options.append({
                    'id': a['id'],
                    'title': a['title'],
                    'organization': a['organization'],
                })

    selected_options = []
    for m in matching_options:
        print('"' + m['title'] +'" from "' + m['organization']['title'] + '"')
        include = ''
        while include not in ('y', 'Y', 'n', 'N'):
            include = input('Include? (y/n)')
        if include == 'y' or include == 'Y':
            selected_options.append(m)

    pprint.pprint(selected_options, indent=4)

    correct = ''
    while correct not in ('y', 'Y', 'n', 'N'):
        correct = input("Is this correct? (y/n)")

    if correct == 'y' or correct == 'Y':
        title = input('Title for your new query: ')

        filter_spec = [
            {
                'config': {
                    'operator': 'in',
                    'state': 'booked',
                    'activity': s['id'],
                    'organizations': 'all',
                },
                'op': 'add',
                'type': 'campaign_participation',
            } for s in selected_options
        ]

        data = {
            'title': title,
            'org_access': 'suborgs',
            'filter_spec': filter_spec,
        }

        import pdb; pdb.set_trace()
        zetkin_api_post('people/queries', org_id, zetkin_access_token, data)
