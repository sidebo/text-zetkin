import json
import os
import requests
from time import sleep
from dotenv import load_dotenv

ZETKIN_BASE_URL = 'https://api.zetk.in/v1/'
# Load environment variables from .env
load_dotenv()

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
        if response.status_code == 404:
            print("Already merged!")
        else:
            raise Exception("ERROR: Cannot interpret response from " + url)

token = input('Access token: ')

org_id = os.environ.get('ZETKIN_ORG')

file = open('merge.json')
res = json.load(file)

tot = 0
mer = 0
for dup in res['duplicates']:
    tot += 1
    objects = dup['objects']
    first_name = objects[0]['first_name'].strip().lower()
    last_name = objects[0]['last_name'].strip().lower()
    if objects[0]['email'] is None:
        continue
    email = objects[0]['email'].strip().lower()
    ext_id = objects[0]['id']

    priority_idx = -1
    merge = True
    for (idx, o) in enumerate(objects):
        if o['is_user']:
            merge = False
        if o['first_name'].strip().lower() == first_name and o['last_name'].strip().lower() == last_name and o['email'] and o['email'].strip().lower() == email:
            if o['id'] >= ext_id:
                priority_idx = idx
        else:
            merge = False
            break
    if priority_idx == -1:
        merge = False
    if merge:
        mer += 1
        print("Merge objects:")
        #print(objects)
        ids = [objects[priority_idx]['id']]
        ids.extend([o['id'] for o in objects if o['id'] != ids[0]])
        data = {
            'type': 'person',
            'objects': ids,
        }
        print(data)
        print(objects)
        #if mer % 10 == 0:
        #    input('Press enter to continue')
        zetkin_api_post('merges', org_id, token, data)
        print("Merge %d", mer)
        sleep(0.5)
    else:
        print("Do not merge objects:")

print("Total number: ", tot)
print("Merged: ", mer)
