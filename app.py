import streamlit as st
from zetkin import get_access_token, zetkin_api_get, get_option
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
from dotenv import load_dotenv

ZETKIN_BASE_URL = 'https://api.zetk.in/v1/'
TEXT_LIMIT = 160
PRICE_PER_TEXT = 0.35
VAT = 1.25
CURRENCY = 'SEK'

load_dotenv()

ZETKING_ORG_ID = os.environ['ZETKIN_ORG']

people_by_phone = None

# Get Zetkin access token
if 'zetkin_access_token' not in st.session_state:
    st.session_state['zetkin_access_token'] = get_access_token()

try:
    data_cache = open(".data-cache-%s" % ZETKING_ORG_ID, 'rb')
    CACHE = pickle.load(data_cache)
    data_cache.close()
except Exception as e:
    print(e)
    CACHE = {}

SMS_USERNAME = os.environ['46ELKS_API_USER']
SMS_PASSWORD = os.environ['46ELKS_API_PASSWORD']
SMS_FROM = os.environ['46ELKS_PHONE']

st.title('Skicka SMS med Zetkin och 46elks')

options_people = ('Tagg', 'Sökning', 'Aktion', 'SMS-svar')

submit_button_people = None
with st.form(key='people'):
    choice = st.selectbox(
        'Hur vill du hitta personer?',
        options=options_people)
    submit_button_people = st.form_submit_button(label='Välj')

options = None
submit_button_options = None
if submit_button_people:
    if (choice == 'Tagg'):
        options = zetkin_api_get('people/tags', ZETKING_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
    elif (choice == 'Sökning'):
       options = zetkin_api_get('people/queries', ZETKING_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
    
    options_list = {i: get_option(choice, option) for i, option in enumerate(options)}
    with st.form(key='options'):
        choice = st.selectbox(
            'Välj alternativ:',
            options=options_list.values())
        submit_button_options = st.form_submit_button(label='Gå vidare')
if submit_button_options:
    st.write("HEELO")
#
    #        if submit_button:
    #            st.write('Hello there')
    #            #for idx, option in enumerate(options):
    #            #    print(str(idx) + ": " + get_option(choice, option))
    #    


"""
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

"""