import pandas as reader
import csv
import re

# Regular expressions representing IDS-Indata extension ranges (UK and NL)
ids_range = [r'^([+*][4][4][1][6][8][4][3][6][2][0][0-9][0-9]$)',
             r'^([+*][4][4][1][6][8][4][5][7][1][2][3-4][0-9]$)',
             r'^([+*][4][4][1][6][8][4][5][7][1][4][5-9][0-9]$)',
             r'^([+*][4][4][1][6][8][4][5][7][1][8][9][0]$)',
             r'^([+*][4][4][9][9][9][0][0][0][0-9][0-9][0-9][0-9]$)',
             r'^([+*][3][1][4][1][6][7][9][9][6][5][0-9]$)',
             r'^([+*][3][1][9][9][9][1][5][0][6][0][0-9][0-9]$)',
             ]
regexp = re.compile('|'.join(ids_range))

# Opening and converting the Phone book file into a dictionary
with open('IDS-Phone_book.csv', 'r+') as info:
    entries = csv.reader(info, delimiter=',')
    phone_book = [item for item in entries if item]
    phone_book = dict(phone_book)


# Applying E164 format to numbers
def format_e164(data):
    try:
        if data[0].isdigit() and len(data) >= 10:
            data = "+" + data
    except TypeError:
        pass
    finally:
        return data


# Converting unix timestamp to standard time
def unix_to_stdtime(unix):
    if unix != 0:
        unix = reader.to_datetime(unix, errors='coerce', unit='s')
    else:
        unix = None
    return unix

