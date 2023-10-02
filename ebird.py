# This example requires the 'message_content' intent.

from dotenv import load_dotenv
import os

load_dotenv()


import requests


def get_rare_text():
    url = 'https://api.ebird.org/v2/data/obs/US-DC/recent/notable?back=1&detail=full'
    ret = []
    r = requests.get(url, headers={'X-eBirdApiToken': os.getenv('EBIRD_TOKEN')})
    for birddata in r.json():
        """
           {'checklistId': 'CL22854',
        'comName': 'Dickcissel',
        'countryCode': 'US',
        'countryName': 'United States',
        'evidence': 'A',
        'firstName': 'McKinley',
        'hasComments': False,
        'hasRichMedia': True,
        'howMany': 1,
        'lastName': 'Street NFC Station',
        'lat': 38.964932,
        'lng': -77.07835,
        'locId': 'L18743887',
        'locName': '*3914 McKinley Street NW',
        'locationPrivate': True,
        'obsDt': '2023-10-01 00:45',
        'obsId': 'OBS1839972978',
        'obsReviewed': True,
        'obsValid': True,
        'presenceNoted': False,
        'sciName': 'Spiza americana',
        'speciesCode': 'dickci',
        'subId': 'S151193858',
        'subnational1Code': 'US-DC',
        'subnational1Name': 'District of Columbia',
        'subnational2Code': 'US-DC-001',
        'subnational2Name': 'District of Columbia',
        'userDisplayName': 'McKinley Street NFC Station'}]
        """
        checklisturl = f"https://ebird.org/checklist/{birddata['subId']}"
        locationurl = f"https://ebird.org/hotspot/{birddata['locId']}"
        new_item = f"* {birddata['comName']}: [list](<{checklisturl}>) @ [{birddata['locName']}](<{locationurl}>) ({birddata['obsDt']}) - {birddata['userDisplayName']})"

        if new_item not in ret:
            ret.append(new_item)
    return ret
