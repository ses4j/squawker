# This example requires the 'message_content' intent.

import asyncio
from collections import defaultdict
from datetime import datetime
import re
import time
from datetime import datetime, timedelta
import discord
import os
from dotenv import load_dotenv
import logging

import ebird

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

dc_channel = None
dc_area_channel = None

print(f"IS_DOCKER: {os.getenv('IS_DOCKER')}")
TESTING = not os.getenv('IS_DOCKER')
if TESTING:
    dc_channel = 1158230242452836485
    dc_area_channel = 1158582890628657213
else:
    dc_channel = 1158584504965943406
    dc_area_channel = 1158589088350359553

assert TOKEN

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
logger = logging.getLogger('discord')


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

    session = ebird.EBirdClient(os.getenv('EBIRD_USERNAME'), os.getenv('EBIRD_PASSWORD')).session

    if dc_channel:
        client.loop.create_task(background_task(region_code='US-DC', channel_id=dc_channel, session=session))
    if dc_area_channel:
        client.loop.create_task(
            background_task2(lat=38.887732, lng=-77.039092, dist_km=35.0, channel_id=dc_area_channel, session=session)
        )


async def background_task(channel_id, region_code='US-DC', session=None):
    await client.wait_until_ready()
    channel = client.get_channel(channel_id)
    assert channel, f"Couldn't find channel {channel_id}"
    # await channel.send(f"Hi!  RBA Squawker reporting for duty on {region_code}!")

    posted_checklists = await _get_recently_posted_checklists(channel)
    known_reports = []
    last_seen = {}
    while not client.is_closed():
        try:
            results_data = ebird.get_notable_birds(region_code=region_code, num_days_back=1)

            for msg in ebird.get_notable_birds_text(results_data, known_reports, last_seen, posted_checklists, session=session):
                await channel.send(msg)
                await asyncio.sleep(0.1)

            logger.info("Sleeping...")
        except Exception as e:
            logger.exception(f"Error in get_notable_birds({region_code})")
        await asyncio.sleep(60 * 3)

async def _get_recently_posted_checklists(channel):
    posted_checklists = set()
    async for msg in channel.history(limit=100):
            if client.user != msg.author:
                continue
            m = re.search('https://ebird.org/checklist/([a-zA-Z0-9]+)', msg.content)
            if m:
                checklist_id = m.group(1)
                posted_checklists.add(checklist_id)
    return posted_checklists


async def background_task2(channel_id, lat, lng, dist_km, session=None):
    await client.wait_until_ready()
    channel = client.get_channel(channel_id)
    assert channel, f"Couldn't find channel {channel_id}"
    # await channel.send(f"Hi!  RBA Squawker reporting for duty on {lat}, {lng}!")

    posted_checklists = await _get_recently_posted_checklists(channel)
    known_reports = []
    last_seen = {}
    while not client.is_closed():
        try:
            results_data = ebird.get_notable_birds_by_latlng(lat, lng, dist_km, num_days_back=1)

            for msg in ebird.get_notable_birds_text(results_data, known_reports, last_seen, posted_checklists, session=session):
                await channel.send(msg)
                await asyncio.sleep(0.1)

            logger.info("Sleeping...")
        except Exception as e:
            logger.exception(f"Error in get_notable_birds_by_latlng({lat}, {lng})")
        await asyncio.sleep(60 * 3)


# @client.event
# async def on_message(message):
#     print(message.author, client.user, message.content)
#     if message.author == client.user:
#         return

# for msg in ebird.get_rare_text():
#     await message.channel.send(msg)
#     await asyncio.sleep(0.1)

client.run(TOKEN)
