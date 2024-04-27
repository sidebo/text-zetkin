import streamlit as st
from zetkin import get_access_token, zetkin_api_get, prepare_texts
from sms import send_sms
import os
import yaml
import pickle
from datetime import datetime
from dotenv import load_dotenv
from datetime import datetime
from dotenv import load_dotenv
import logging

####
# TODO:
# * DONE Prepare text in some free text field
# * DONE Check that all options work
# * Prepare config such as 46elks credentials somewhere
# * Sometimes the .api-cache file must be deleted. Include something that removes this file when needed? 
# * Make docker image
# * Deploy somewhere, Google?
####

st.set_page_config(layout="wide")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("app")

ZETKIN_BASE_URL = 'https://api.zetk.in/v1/'
TEXT_LIMIT = 160
PRICE_PER_TEXT = 0.35
VAT = 1.25
CURRENCY = 'SEK'

load_dotenv()

DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("true", "t", "1")
DEFAULT_CAMPAIGN = os.getenv("DEFAULT_CAMPAIGN")

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

def _action_name(action) -> str:
    if action["title"] and action["activity"] and action["activity"]["title"]:
        return f'{action["title"]}: {action["activity"]["title"]}'
    elif action["title"]:
        return action["title"]
    elif action["activity"] and action["activity"]["title"]:
        return action["activity"]["title"]
    else:
        return "UNKNOWN_ACTION_NAME"

def send_texts(people, text, choice, action=None):
    # TODO: vad har choice för betydelse?
    assert text is not None and text != "", "Text is empty or None!"
    people = [person for person in people if person['phone'] is not None]

    st.write('Förbereder för att skicka SMS till: ')
    for p in people:
        st.write(f"- {p['first_name']} {p['last_name']}, {p['phone']}")

    (texts, over_limit_count, total_text_count) = prepare_texts(text, people, action)

    st.write("%d/%d sms över teckengränsen!" % (over_limit_count, len(people)))

    st.write("Detta kommer kosta %.2f %s" % (total_text_count*PRICE_PER_TEXT*VAT, CURRENCY))

    st.write("Första meddelandet:")
    st.caption(texts[0]['text'])


    send = st.button("SKICKA SMS")
    
    if send:
        nr_successfully_sent = 0
        with open('log.yaml', 'a') as log_file:
            for text in texts:
                if not DRY_RUN:
                    log = send_sms(text['text'],text['phone'], SMS_USERNAME, SMS_PASSWORD, SMS_FROM) 
                    yaml.safe_dump(log, log_file)
                    nr_successfully_sent += (log['response']['status'] == 201)
                else:
                    logger.info("DRY_RUN flagged, not sending!")

        st.write(f"{nr_successfully_sent}/{len(people)} sms skickade!")   


st.title('Skicka SMS med Zetkin och 46elks')

col1, col2 = st.columns([2, 1])

def _get_text() -> str:
    example_text = 'Hej {person.first_name}! Detta är en påminnelse om lördagens aktion...'
    with col2:
        text = st.text_area('SMS-innehåll', example_text, placeholder=example_text)
        return text


### CHAIN OF CHOICES
# No support for texting those that replied to SMS, like existed in Niklas original script.
# See his repo for code https://github.com/niklasva82/text-zetkin.git for details on that.
options_people = ('Tagg', 'Sökning', 'Aktion/Kampanj')
    
with col1:
    # 1) Chose how to select people
    choice_people = st.selectbox(
        'Hur vill du hitta personer?',
        options=options_people,
        index=None)
        
        
    # 2) Chose which tag/query/action
    if choice_people is not None:
        # Get options of tag/query/action
        options = None
        if (choice_people == 'Tagg'):
            options = zetkin_api_get('people/tags', ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
        elif (choice_people == 'Sökning'):
           options = zetkin_api_get('people/queries', ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
        elif (choice_people == 'Aktion/Kampanj'):
            options = zetkin_api_get('campaigns', ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
    
        options = {i: o for i, o in enumerate(options)}
        options_list = [f"{i}: {o['title']}" for i, o in options.items()]

        default_choice_filter_idx = None
        if choice_people == "Aktion/Kampanj" and DEFAULT_CAMPAIGN is not None:
            for idx, o in options.items():
                if o['title'] == DEFAULT_CAMPAIGN:
                    default_choice_filter_idx = idx
                    break

        choice_filter = st.selectbox(
                f"Välj {choice_people.lower()}",
                options=options_list,
                index=default_choice_filter_idx,
                disabled=choice_people is None)
        
        # Send texts
        if choice_people and choice_filter:
            choice_filter_idx = int(choice_filter.split(":")[0])
            choice_filter = options[choice_filter_idx]

            text = _get_text()
        
            if choice_people == 'Sökning':
                people = zetkin_api_get('people/queries/%d/matches' % choice_filter['id'], ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
                send_texts(people, text, choice_people)
            elif choice_people == 'Tagg':
                people = zetkin_api_get('people/tags/%d/people' % choice_filter['id'], ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
                send_texts(people, text, choice_people)
            elif choice_people == 'Aktion/Kampanj':
                # Get campaigns
                today = datetime.now().strftime('%Y-%m-%d')
                campaign_actions = zetkin_api_get('campaigns/%d/actions?filter=start_time>%s>' % (choice_filter['id'], today), ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
                
                if not campaign_actions:
                    st.write("Inga framtida aktioner finns! Välj en annan kampanj.")
                
                else:
                    # Filter any actions without contacts
                    campaign_actions = [action for action in campaign_actions if action['contact']]
                    if not campaign_actions:
                        st.write("Inga framtida aktioner med kontaktpersoner. Välj en annan kampanj!")
            
                    action_id_to_name = {a["id"]: _action_name(a) for a in campaign_actions}
                    action_name_to_id = {_action_name(a): a["id"] for a in campaign_actions}
                    action_names = [_action_name(a) for a in campaign_actions]
                    
                    # 3) Which actions
                    with st.form(key="Välj aktion(er):"):
                        
                        container = st.container()
                        all_ = st.checkbox("Välj alla")
                        
                        if all_:
                            selected_actions = container.multiselect("Välj aktion(er):",
                                    action_names, action_names)
                        else:
                            selected_actions =  container.multiselect("Välj aktion(er):", action_names)
                        submit_button = st.form_submit_button(label="Klar")
                    if submit_button:
                        st.write("Du valde aktioner: ", selected_actions) 
                        selected_action_ids = [action_name_to_id[n] for n in selected_actions]      
                        campaign_actions = campaign_actions if all_ else \
                            [ca for ca in campaign_actions if ca["id"] in selected_action_ids]

                        for action in campaign_actions:
                            people = zetkin_api_get('actions/%d/participants' % action['id'], ZETKIN_ORG_ID, st.session_state['zetkin_access_token'], CACHE)
                            send_texts(people, text, choice_people, action)