import streamlit as st
from zetkin import get_access_token, zetkin_api_get, get_option, prepare_texts
from sms import send_sms, format_phone
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

ZETKIN_ORG_ID = os.environ['ZETKIN_ORG']

people_by_phone = None

# Get Zetkin access token
if 'zetkin_access_token' not in st.session_state:
    st.session_state['zetkin_access_token'] = get_access_token()

try:
    data_cache = open(".data-cache-%s" % ZETKIN_ORG_ID, 'rb')
    CACHE = pickle.load(data_cache)
    data_cache.close()
except Exception as e:
    print(e)
    CACHE = {}

SMS_USERNAME = os.environ['46ELKS_API_USER']
SMS_PASSWORD = os.environ['46ELKS_API_PASSWORD']
SMS_FROM = os.environ['46ELKS_PHONE']

def send_texts(people, text, choice, action=None):
    assert text is not None and text != "", "Text is empty or None!"
    people = [person for person in people if person['phone'] is not None]

    st.write('Skicka till: ')
    st.write('\n- '.join([f"{p['first_name']} {p['last_name']}" for p in people]))

    (texts, over_limit_count, total_text_count) = prepare_texts(text, people, action)

    st.write("%d/%d sms över teckengränsen!" % (over_limit_count, len(people)))

    st.write("Detta kommer kosta %.2f %s" % (total_text_count*PRICE_PER_TEXT*VAT, CURRENCY))

    #st.write("Please review the first text:\n")
    #st.write("Recipient: %s" % texts[0]['phone'])
    st.write("Första meddelandet:")
    st.caption(texts[0]['text'])

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
        pass
        #st.write("\nPlease reivew the %d people that you have chosen to text as part of the %s" % (len(people), _type))
        #st.write("Press enter when you want to move to the nex page")
#
        #idx = 0
        #PAGE_SIZE = 20
        #while idx < len(texts):
        #    input("\nPress enter to continue\n")
        #    for text in texts[idx:idx+PAGE_SIZE]:
        #        print("%s, %s" % (text['name'], text['phone']))
        #    idx += PAGE_SIZE
#
        #print(texts[0]['text'])

    #print("\n\nHave you reviewed all the information and want to send this message? Type SEND, otherwise type SKIP. If you're not satisfied with text, type EDIT")
    send = st.button("SKICKA SMS")
    #while send not in ["SEND", "SKIP"]:
    #    if send == "EDIT":
    #        #text = edit_text_file()
    #        (texts, over_limit_count, total_text_count) = prepare_texts(text, people)
    #        print("Please review the first text:\n")
    #        print("Recipient: %s" % texts[0]['phone'])
    #        print(texts[0]['text'])
#
    #        print("%d/%d texts over the text limit!" % (over_limit_count, len(people)))
#
    #        print("This will cost %.2f %s" % (total_text_count*PRICE_PER_TEXT*VAT, CURRENCY))
#
    #    send = input()

    if send:
        nr_successfully_sent = 0
        with open('log.yaml', 'a') as log_file:
            for text in texts:
                log = send_sms(text['text'],text['phone'], SMS_USERNAME, SMS_PASSWORD, SMS_FROM)
                yaml.safe_dump(log, log_file)
                nr_successfully_sent += (log['response']['status'] == 201)

        st.write(f"{nr_successfully_sent}/{len(people)} sms skickade!")   



st.title('Skicka SMS med Zetkin och 46elks')

options_people = ('Tagg', 'Sökning', 'Aktion', 'SMS-svar')

col_main, col_status = st.columns([3, 1])

with col_status:
    st.write("Dina val:")
    st.write(f"Hitta personer: {st.session_state.get('choice_people', '-')}")
    st.write(f"Alternativ: {st.session_state.get('choice_filter', '-')}")
    if st.button("Rensa"):
        del st.session_state['choice_people']
        del st.session_state['choice_filter']

with col_main:
    # Chose how to select people
    if 'choice_people' not in st.session_state:
        choice_people = st.selectbox(
            'Hur vill du hitta personer?',
            options=options_people)
        submit_button_people = st.button(label='Välj')
        if submit_button_people:
            st.session_state['choice_people'] = choice_people
    
    # Chose which tag/query/action
    if 'choice_people' in st.session_state and 'choice_filter' not in st.session_state:
        choice_people = st.session_state['choice_people']
        if (choice_people == 'Tagg'):
            options = zetkin_api_get('people/tags', ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
        elif (choice_people == 'Sökning'):
           options = zetkin_api_get('people/queries', ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
        elif (choice_people == 'Aktion'):
            options = zetkin_api_get('campaigns', ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
        elif (choice_people == 'SMS-svar'):
            raise NotImplementedError(choice_people)
            """
            people = zetkin_api_get('people', org_id, zetkin_access_token)
            if people_by_phone is None:
                people_by_phone = get_people_by_phone(people)
            options = sms_get_replies(SMS_USERNAME, SMS_PASSWORD, SMS_FROM)
        """
        else:
            raise NotImplementedError(choice_people)
        
        options_list = [f"{i}: {get_option(choice_people, option)}" for i, option in enumerate(options)]
        
        choice_filter = st.selectbox(
                'Välj alternativ:',
                options=options_list)
        choice_filter = int(choice_filter.split(":")[0])
        submit_button_filter = st.button(label='Gå vidare')
        if submit_button_filter:
            st.session_state['choice_filter'] = options[choice_filter]
    
    # Send texts
    if 'choice_people' in st.session_state and 'choice_filter' in st.session_state:
        choice_people = st.session_state['choice_people']
        choice_filter = st.session_state['choice_filter']
        text = "DUMMY TEXT"
        if choice_people == 'Sökning':
            people = zetkin_api_get('people/queries/%d/matches' % choice_filter['id'], ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
            send_texts(people, text, choice_people)
        elif choice_people == 'Tagg':
            people = zetkin_api_get('people/tags/%d/people' % choice_filter['id'], ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
            send_texts(people, text, choice_people)
        elif choice_people == 'SMS-svar':
            raise NotImplementedError(choice_people)
            phone = option['from']
            print_phone_history(option)
            send_texts([{
                    'phone': phone,
                    'first_name': '',
                    'last_name': '',
                }], text, choice)
        elif choice_people == 'Aktion':
            today = datetime.now().strftime('%Y-%m-%d')
            campaign_actions = zetkin_api_get('campaigns/%d/actions?filter=start_time>%s>' % (choice_filter['id'], today), ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
        
            # Filter any actions without contacts
            campaign_actions = [action for action in campaign_actions if action['contact']]
        
            for action in campaign_actions:
                action['start_time'] = parser.parse(action['start_time'])
                action['end_time'] = parser.parse(action['end_time'])
        
                # If not contact has been assigned, skip the action
                if not action['contact']:
                    continue
        
                contact = zetkin_api_get('people/%d' % action['contact']['id'], ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
        
                # Format phone number
                phone = format_phone(contact['phone'])
                contact['phone'] = phone
        
                action['contact'] = contact
        
            
            for idx, action in enumerate(campaign_actions):
                print("%d: %s, %s, %s" % (idx,
                                          action['title'] if action['title'] else action['activity']['title'],
                                          action['location']['title'],
                                          action['start_time'].strftime('%Y-%m-%d %H:%M')))
        
            #action_choice = st.selectbox(
            #    'Which action(s)?',
            #    ZETKIN_ORG_ID, st.session_state['zetkin_access_token']))
        
    #campaign_actions = campaign_actions if action_choice == "ALL" else \
    #    [campaign_actions[idx] for idx in [int(ac.strip()) for ac in action_choice.split(",")]]
    
    #for action in campaign_actions:
    #    people = zetkin_api_get('actions/%d/participants' % action['id'], ZETKIN_ORG_ID, st.session_state['zetkin_access_token'])
    #    send_texts(people, text, choice_people, action)


"""
elif(choice == 'a'):
    options = zetkin_api_get('campaigns', org_id, zetkin_access_token)
elif(choice == 'r'):
    

    print("Choose from these options: ")
    for idx, option in enumerate(options):
        print(str(idx) + ": " + get_option(choice, option))

    option_idx = ''
    while not option_idx.isdigit():
        option_idx = input("Which option? ")

    option = options[int(option_idx)]



"""