This repository contains scripts that sends texts to people in the Zetkin platform.
People are selected through matching by queries, tags or participants in actions.

NOTE: Currently only texts Swedish mobile phone numbers.

## 46elks setup
The 46elks API is used to send text messages.
To create a new account, follow these steps:
- Create a 46elks.se account.
- Buy a 46elks.se phone number.
- Get the 46elks.se API username, password and the phone number you wish to send from (in international format)
- Fill the `.env` file with the username, password and phone number.

## Python environment setup
Install via pip [NOT TESTED]:
```pip install -r requirements.txt```

Install a conda env (recommended) (requires anaconda/miniconda):
```
conda env create -f environment.yml
conda activate zetkin
```

## Send text
- Type a text using the format in sample-text.txt
- Run with `python text.py text.txt`, follow the instructions.
- The script will prompt for Zetkin access token. Log in to Zetkin Organize->People and get your access token (inspector -> network tab -> reload -> filter xhr -> click optional GET request -> copy token after "Bearer")
- Fill
