# This example requires the 'message_content' intent.

import asyncio
from collections import defaultdict
from datetime import datetime
import re
import sys
import time
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging

import discord

# from discord import Webhook, AsyncWebhookAdapter
from discord.ext import commands

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

# client = discord.Client(intents=intents)
logger = logging.getLogger('discord')


bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    description="Squawker! Your friendly neighbord bird-bot.",
)
# bot._ignore_list = data_utils.get_filter_wordlist()


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

    try:
        session = ebird.EBirdClient(os.getenv('EBIRD_USERNAME'), os.getenv('EBIRD_PASSWORD')).session
    except:
        sys.exit(1)
    assert session
    if dc_channel:
        bot.loop.create_task(background_task(region_code='US-DC', channel_id=dc_channel, session=session))
    if dc_area_channel:
        bot.loop.create_task(
            background_task2(lat=38.887732, lng=-77.039092, dist_km=35.0, channel_id=dc_area_channel, session=session)
        )


async def background_task(channel_id, region_code='US-DC', session=None):
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    assert channel, f"Couldn't find channel {channel_id}"
    # await channel.send(f"Hi!  RBA Squawker reporting for duty on {region_code}!")

    posted_checklists = await _get_recently_posted_checklists(channel)
    known_reports = []
    last_seen = {}
    while not bot.is_closed():
        try:
            results_data = ebird.get_notable_birds(region_code=region_code, num_days_back=1)

            for msg in ebird.get_notable_birds_text(
                results_data, known_reports, last_seen, posted_checklists, session=session
            ):
                await channel.send(msg)
                await asyncio.sleep(0.1)

            logger.info("Sleeping...")
        except Exception as e:
            logger.exception(f"Error in get_notable_birds({region_code})")
        await asyncio.sleep(60 * 3)


async def _get_recently_posted_checklists(channel):
    posted_checklists = set()
    async for msg in channel.history(limit=100):
        if bot.user != msg.author:
            continue
        m = re.search('https://ebird.org/checklist/([a-zA-Z0-9]+)', msg.content)
        if m:
            checklist_id = m.group(1)
            posted_checklists.add(checklist_id)
    return posted_checklists


async def background_task2(channel_id, lat, lng, dist_km, session=None):
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    assert channel, f"Couldn't find channel {channel_id}"
    # await channel.send(f"Hi!  RBA Squawker reporting for duty on {lat}, {lng}!")

    posted_checklists = await _get_recently_posted_checklists(channel)
    known_reports = []
    last_seen = {}
    while not bot.is_closed():
        try:
            results_data = ebird.get_notable_birds_by_latlng(lat, lng, dist_km, num_days_back=1)

            for msg in ebird.get_notable_birds_text(
                results_data, known_reports, last_seen, posted_checklists, session=session
            ):
                await channel.send(msg)
                await asyncio.sleep(0.1)

            logger.info("Sleeping...")
        except Exception as e:
            logger.exception(f"Error in get_notable_birds_by_latlng({lat}, {lng})")
        await asyncio.sleep(60 * 3)


# @bot.event
# async def on_message(message):
#     print(message.author, bot.user, message.content)
#     if message.author == bot.user:
#         return


# for msg in ebird.get_rare_text():
#     await message.channel.send(msg)
#     await asyncio.sleep(0.1)
import random

salutations = [
    'my boy!',
    'friend.',
    'buddy.',
    'my dude.',
    'bestie!',
    'young bird padawan.',
    'child.',
]


@bot.command()
async def whats(ctx, *input: str):
    """Look up a 4 letter bird code."""
    logger.info(f"whats: {input}")
    code = " ".join([str(c) for c in input]).lower()
    import fourletter

    if len(code) < 3:
        msg = "Please provide at least 3 characters."
        await ctx.send(msg)
        return

    if len(code) == 6 or len(code) == 4:
        common_name = fourletter.get_common_name_by_code(code)
        if not common_name:
            msg = "Sorry, I don't know that code."
        else:
            salutation = random.choice(salutations)
            msg = f"{code} is the code for **{common_name}**, {salutation}"
        await ctx.send(msg)
        return
    else:
        results = []
        MAX_RESULTS = 5
        for code4, comname in fourletter.code_by_common_name_substring(code, max_items=MAX_RESULTS + 1):
            msg = f"{code4} is the code for **{comname}**."
            results.append(msg)

        if not results:
            msg = "Sorry, I can't find any matching birds."
            await ctx.send(msg)
        else:
            for msg in results[:MAX_RESULTS]:
                await ctx.send(msg)
                await asyncio.sleep(0.1)
            if len(results) > MAX_RESULTS:
                await ctx.send("...there are the first 5 results, but there are more.")


bot.run(TOKEN)
