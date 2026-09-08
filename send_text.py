import requests
import os
from dotenv import load_dotenv
import pandas as pd
from sms import normalize_phone, send_sms
import math

TEXT_LIMIT = 160
PRICE_PER_TEXT = 0.5
VAT = 1.25
CURRENCY = 'SEK'

load_dotenv()

API_USERNAME = os.environ["46ELKS_API_USER"]
API_PASSWORD = os.environ["46ELKS_API_PASSWORD"]
DRY_RUN=os.getenv("DRY_RUN", "true").lower() == "true"

#INPUT_FILE = "input/Ej betalt årets medlemsavgift (inkl belopp & OCR) 2025_12_21.csv"
INPUT_FILE = "input/allamedlemmar-20260907.csv"


def read_text_file(filename):
    with open(filename, "rt") as f:
        lines = f.readlines()
        text = ''.join(lines)
        text = text.strip()
    return text

###### 
df = pd.read_csv(INPUT_FILE, usecols=['Förnamn', 'Efternamn','Mobiltelefon'])

df["Mobiltelefon"] = df["Mobiltelefon"].map(normalize_phone)
missing_phone_nr = df["Mobiltelefon"].isna()
if missing_phone_nr.sum() > 0:
    print("Kan inte skicka pga saknat eller utländskt mobilnummer:")
    print(df.loc[missing_phone_nr, ["Förnamn", "Efternamn"]])
    df = df[~missing_phone_nr]

content_template = \
"""Hej {Fornamn}!
DU BEHÖVS FÖR ATT VINNA VALET!
På söndag kan vi byta regering. Men då behövs du! Välj hur du vill bidra:
DÖRRKNACK olika platser i Sthlm 8,9,10 sep: tinyurl.com/knacksthlm
FLYGBLAD 12/9: tinyurl.com/vhsv26
DÖRRKNACK VALDAGEN: tinyurl.com/knkval26
NU KÖR VI!
V Hammarby-Skrpnck
"""
df = df[df["Förnamn"] != "Edvin"]
if len(df) > 0:
    for _, person in df.iterrows():
        text_content = content_template.format(Fornamn=person["Förnamn"]) #, Belopp=person["SenastReskontra_AviseratBelopp"][:3], OCR=person["SenastReskontra_OCR"])
        total_text_count = math.ceil(len(text_content)/TEXT_LIMIT)
        print("På väg att skicka till\n", list(person), "\nmeddelande: \n'", text_content, "'", "len(text_content)=", len(text_content))
        # NB: seems to be slightly wrong, understimating... check 46elks on a test sms to be sure.
        print("This will cost %.2f %s" % (total_text_count*PRICE_PER_TEXT*VAT, CURRENCY))
        if not DRY_RUN:
            ret = send_sms(text_content, person["Mobiltelefon"], API_USERNAME, API_PASSWORD, from_="VHS")
            response = ret['response']
            if response['status'] != 200:
                print("ERROR kunde inte skicka till ", person)
                print(response['body'])
            else:
                print("Skickat och klart!")
        else:
            print("DRY_RUN flaggat. Skickar inget.")
else:
    print("Empty df! nothing to do.")

