import requests
import phonenumbers

BASE_URL_46ELKS = "https://api.46elks.com/a1/sms"

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

def send_sms(text, phone, username, password, from_number):
    print("Send SMS to %s: %s" % (phone, text))
    resp = requests.post(
        BASE_URL_46ELKS,
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
