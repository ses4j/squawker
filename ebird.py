# This example requires the 'message_content' intent.

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
import functools
import time
from datetime import datetime, timedelta
from typing import Any, Collection
import discord
import os
from dotenv import load_dotenv
import logging, re
import pytz


load_dotenv()


import requests

logger = logging.getLogger('bot.ebird')
REPORT_IS_TOO_OLD_AFTER_HOURS = 24

global _histogram_data_cache
_histogram_data_cache = {}
cache_path = "_cache1"

year = datetime.now().year
tenyearsago = year - 10
from html.parser import HTMLParser


class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.execution_value = None

    def handle_starttag(self, tag, attrs):
        # Check if the tag is 'input' and has name='execution'
        if tag == 'input':
            attr_dict = dict(attrs)
            if attr_dict.get('name') == 'execution':
                self.execution_value = attr_dict.get('value')


class EBirdClient(object):
    def __init__(self, username, password):
        self.username = username
        assert self.username, 'need username'
        self.session = self._login(username, password)

    @staticmethod
    def _login(username, password):
        logger.debug('starting login...')
        s = requests.Session()

        logger.debug(f'Logging in as {username}...')
        r = s.get('https://ebird.org/myebird/US', allow_redirects=True)
        # breakpoint()
        # m = re.search(r'<input type=\"hidden\" name=\"lt\" value=\"([^"]+)\"', r.text)
        # lt = m.group(1)

        parser = FormParser()
        parser.feed(r.text)

        assert parser.execution_value
        # breakpoint()
        # m = re.search(r'<input type=\"hidden\" name=\"execution\" value=\"([^"]+)\"', r.text)
        # execution = m.group(1)

        payload = {
            # "service": "https://ebird.org/login/cas?portal=ebird",
            "locale": "en_US",
            "username": username,
            "password": password,
            "rememberMe": "on",  # Checkbox is checked
            "execution": parser.execution_value,
            "_eventId": "submit",
        }

        r = s.post(
            r.url,
            data=payload,
            # data={'username': username, 'password': password, 'lt': lt, 'execution': 'e1s1', '_eventId': 'submit'},
            allow_redirects=True,
        )

        assert r.status_code == 200, f"Login failed: {r.status_code} - {r.text}"
        logger.debug(f'Logged in successfully.')

        return s


def ellipse(s, max_chars=2900):
    if not s:
        return s

    if len(s) > max_chars:
        return s[:max_chars] + "..."
    else:
        return s


def get_quarter_index_of_date(date_value):
    # index = (date_value.month-1)//3
    ##
    day_offset = round(((date_value.day - 1) / 31.0 * 4.0) - 0.49)
    index = (date_value.month - 1) * 4 + day_offset

    return index


def _get_histogram_indexes(date_quarter_index, include_nearby_samples=0):
    for idx in range(
        date_quarter_index - include_nearby_samples,
        date_quarter_index + include_nearby_samples + 1,
    ):
        yield idx


# @functools.lru_cache(maxsize=20000)
def get_bird_sighting_frequency(
    species_full_name,
    date_value: datetime | None = None,
    date_quarter_index=None,
    area="US-DC",
    include_nearby_samples=1,
    session=None,
):
    """Get the % likelihood that a given species is reported at a given time.
    Time can be specified by a datetime.date in `date_value` XOR an int `date_quarter_index` (0-3).
    """

    if date_quarter_index is None:
        date_quarter_index = get_quarter_index_of_date(date_value)
    histogram_data = get_all_histogram_data(area, session=session)

    # sample_size = histogram_data.sample_sizes[date_quarter_index]
    # if sample_size < min_sample_size:
    #     return None
    total = 0.0
    sightings = 0.0
    for idx in _get_histogram_indexes(date_quarter_index, include_nearby_samples):
        sightings += histogram_data[species_full_name][idx] * histogram_data.sample_sizes[idx]
        total += histogram_data.sample_sizes[idx]

    return sightings / total


def fetch_data(url, filename, expires=None, headers=None, require_200=True, session=None):
    """Fetch (and cache) `url` into filename."""

    if not os.path.exists(cache_path):
        os.mkdir(cache_path)

    filepath = os.path.join(cache_path, filename)
    if not os.path.exists(filepath):
        logger.info("{} does not exist -- downloading from {}.".format(filepath, url))
        if session:
            data = session.get(url, headers=headers)
        else:
            data = requests.get(url, headers=headers)
        if require_200:
            # if data.status_code != 200:
            #     import pdb; pdb.set_trace()
            assert data.status_code == 200, "{} - {}".format(data.status_code, data.text)
        assert data.headers['Content-Type'] != 'text/html;charset=UTF-8', data.text

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(data.text)
    else:
        logger.debug("{} exists -- using cache for {}.".format(filepath, url))

    return open(filepath, encoding="utf-8").read()


def get_all_histogram_data(area="US-DC", session=None):
    global _histogram_data_cache

    try:
        return _histogram_data_cache[area]
    except KeyError:
        pass

    # url = "http://ebird.org/ebird/BarChart?cmd=getChart&displayType=download&getLocations=states&states={}&bYear=2006&eYear=2016&bMonth=1&eMonth=12&reportType=location&".format(area)
    url = f"https://ebird.org/barchartData?r={area}&bmo=1&emo=12&byr={tenyearsago}&eyr={year}&fmt=tsv"
    # import pdb; pdb.set_trace()

    data = fetch_data(
        url, f"histogram-data-{area}-{tenyearsago}-{year}.tsv", require_200=False, session=session
    )  # sometimes these dont work.
    if not data:
        raise RuntimeError("bad histogram data.")

    class SpeciesData(dict):
        def __init__(self):
            self.sample_sizes = None

    species_data = SpeciesData()
    begin = False

    for row in data.split("\n"):
        if not row:
            continue

        if not begin:
            if row.startswith("Sample Size:"):
                begin = True
                sample_sizes = row.strip().split("\t")[1:]
                try:
                    species_data.sample_sizes = [int(float(x)) for x in sample_sizes]
                except:
                    import pdb

                    pdb.set_trace()

            continue

        species, frequencies = row.split("\t", 1)

        # Sometimes species has italics of the scientific name, maybe depending on settings...
        species = species.split(" (<em ", 1)[0]
        if species.endswith("sp."):
            # print('skipped', species)
            continue
        if species.endswith("sp.)"):
            # print('skipped', species)
            continue
        if "/" in species:
            # print('skipped', species)
            continue
        if "hybrid" in species:
            # print('skipped', species)
            continue
        if "Domestic" in species:
            # print('skipped', species)
            continue
        species_data[species] = [float(x) for x in frequencies.strip().split("\t")]

    _histogram_data_cache[area] = species_data
    return species_data

    # pprint.pprint(species_data)


def get_notable_birds(region_code='US-DC', num_days_back=2):
    url = f'https://api.ebird.org/v2/data/obs/{region_code}/recent/notable?back={num_days_back}&detail=full'
    r = requests.get(url, headers={'X-eBirdApiToken': os.getenv('EBIRD_TOKEN')})
    assert r.status_code == 200, r.text
    return r.json()


def get_notable_birds_by_latlng(lat, lng, dist_km, num_days_back=2):
    assert dist_km <= 50
    DC = 38.887732, -77.039092
    url = f'https://api.ebird.org/v2/data/obs/geo/recent/notable?back={num_days_back}&detail=full&lat={lat}&lng={lng}&dist={dist_km}'
    r = requests.get(url, headers={'X-eBirdApiToken': os.getenv('EBIRD_TOKEN')})
    assert r.status_code == 200, r.text
    return r.json()


def get_checklist_info(subId: str):
    url = f"https://api.ebird.org/v2/product/checklist/view/{subId}"
    r = requests.get(url, headers={'X-eBirdApiToken': os.getenv('EBIRD_TOKEN')})
    assert r.status_code == 200, r.text
    return r.json()


def get_info_about_sighting(subId: str, obsId: str) -> dict[str, Any] | None:
    data = get_checklist_info(subId)
    obses = data.pop('obs')
    # import pprint; pprint.pprint(data)
    dur = data.get('durationHrs')
    for obs in obses:
        if obs['obsId'] == obsId:
            obs['durationHrs'] = dur
            return obs
    return None

    # obs = {
    #   "speciesCode": "cacgoo1",
    #   "hideFlags": [],
    #   "obsDt": "2018-01-04 18:29",
    #   "subnational1Code": "US-NY",
    #   "howManyAtleast": 1,
    #   "howManyAtmost": 1,
    #   "howManyStr": "1",
    #   "present": false,
    #   "projId": "EBIRD",
    #   "subId": "S29893687",
    #   "obsId": "OBS406047820",
    #   "obsAux": [
    #     {
    #       "subId": "S29893687",
    #       "obsId": "OBS406047820",
    #       "speciesCode": "cacgoo1",
    #       "fieldName": "breeding_code",
    #       "entryMethodCode": "ebird_breeding",
    #       "auxCode": "UN",
    #       "value": "C4"
    #     }
    #   ]
    # }


def interpret_naive_as_local(naive_dt):
    return pytz.timezone('US/Eastern').localize(naive_dt)


def now():
    return datetime.now(timezone.utc).astimezone()


def markup_url(text, url):
    # [{r['locName']}](<{locationurl}>)
    return f"[{text}](<{url}>)"


def get_notable_birds_text(
    results_data,
    known_reports: list[str] | None = None,
    last_seen: dict[tuple[str, str], datetime] | None = None,
    posted_checklists: Collection[str] | None = None,
    session: requests.Session | None = None,
):
    ctr = 0
    if known_reports is None:
        known_reports = []
    if last_seen is None:
        last_seen = {}
    if posted_checklists is None:
        posted_checklists = set()

    for r in reversed(results_data):
        if r['obsId'] in known_reports:
            continue
        ctr += 1
        if ctr > 20:
            break
        known_reports.append(r['obsId'])

        key = (r['comName'], r['locName'])
        dt = interpret_naive_as_local(datetime.strptime(r['obsDt'], "%Y-%m-%d %H:%M"))

        checklisturl = f"https://ebird.org/checklist/{r['subId']}"

        if r['locationPrivate']:
            locationurl = f"https://www.google.com/maps/search/?api=1&query={r['lat']},{r['lng']}"
        else:
            locationurl = f"https://ebird.org/hotspot/{r['locId']}"
        ago = (now() - dt).total_seconds() / 60
        ago = f"{ago:.0f}m ago" if ago < 60 else f"{ago/60:.0f}h ago"

        if session:
            try:
                region_code = r['subnational2Code'] or r['subnational1Code']
                freq = get_bird_sighting_frequency(r['comName'], now(), area=region_code, session=session)
                freq = f"{freq*100:.1f}%"
                freq = markup_url(
                    freq,
                    f"https://ebird.org/barchart?r={region_code}&bmo=1&emo=12&byr={tenyearsago}&eyr={year}&spp={r['speciesCode']}",
                )
            except KeyError:
                freq = '_never_'
        else:
            freq = ''

        obs = get_info_about_sighting(r['subId'], r['obsId'])
        comments: str | None = obs.get('comments')
        howManyStr = obs.get('howManyStr')
        durationHrs = obs.get('durationHrs')
        # import pprint
        # pprint.pprint(obs)
        howmany = ''
        if howManyStr:
            try:
                howmany = int(howManyStr)
                if howmany > 1:
                    howmany = f" x{howmany}"
                else:
                    howmany = ''
            except:
                pass

        msg = f"**{r['comName'].upper()}**{howmany}, {markup_url(r['locName'], locationurl)} @ {markup_url(r['obsDt'], checklisturl)} ({ago}, {freq}) h/t *{r['userDisplayName']}*."
        if comments:
            msg += "\n> " + ellipse(comments.strip(), 255)

        if now() - dt > timedelta(hours=REPORT_IS_TOO_OLD_AFTER_HOURS):
            logger.info(f"Skipping too-old report: {msg}")
            continue

        if key not in last_seen:
            last_seen[key] = dt
            is_continuing = False
        else:
            is_continuing = dt - last_seen[key] < timedelta(hours=24)
            if dt - last_seen[key] < timedelta(minutes=45):
                logger.info(f"Skipping already-reported: {msg}")
                continue

        if dt > last_seen[key]:
            last_seen[key] = dt

        msg = "Continuing " + msg if is_continuing else msg

        if r['subId'] in posted_checklists:
            # this is so i don't repeat recently posted history when restarting...
            logger.info(f"Skipping already-posted checklist: {msg}")
            continue
        elif is_continuing:
            logger.info(f"Found continuing bird: {msg}")
        else:
            logger.info(f"Found new bird: {msg}")

        yield msg


def get_rare_text(region_code='US-DC', num_days_back=7):
    results_data = get_notable_birds(region_code=region_code, num_days_back=num_days_back)

    rets = defaultdict(list)

    for birddata in results_data:
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

        key = f"*{birddata['comName']}* @ [{birddata['locName']}](<{locationurl}>)"
        new_item = f"[{birddata['obsDt']}](<{checklisturl}>) {birddata['userDisplayName']}"
        if new_item not in rets[key]:
            rets[key].append(new_item)

    ret = []
    for key, sightings in rets.items():
        if len(sightings) == 1:
            ret.append(f"* {key}: {sightings[0]}")
        elif len(sightings) < 4:
            ret.append(f"* {key}: {', '.join(reversed(sightings))}")
        else:
            ret.append(f"* {key}: {len(sightings)} sightings from {sightings[-1]} to {sightings[0]}")

    return ret


if __name__ == '__main__':
    ebird = EBirdClient(os.getenv('EBIRD_USERNAME'), os.getenv('EBIRD_PASSWORD'))

    REPORT_IS_TOO_OLD_AFTER_HOURS = 1000
    results_data = get_notable_birds(region_code='US-DC', num_days_back=7)
    # print(results_data)
    for msg in get_notable_birds_text(results_data):
        print(msg)

    # ebird = EBirdClient(os.getenv('EBIRD_USERNAME'), os.getenv('EBIRD_PASSWORD'))
    # session = ebird.session

    # h = get_all_histogram_data(session=session)
    # print(get_bird_sighting_frequency("Blackpoll Warbler", now(), area='US-DC', session=session))
