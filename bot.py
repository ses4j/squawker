# This example requires the 'message_content' intent.

import asyncio
from collections import defaultdict
from datetime import datetime
import re
import sys
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
import fourletter

import discord

from discord.ext import commands

import ebird

logger = logging.getLogger('bot')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

dc_channel = None
dc_area_channel = None

print(f"IS_DOCKER: {os.getenv('IS_DOCKER')}")
TESTING = not os.getenv('IS_DOCKER')
if TESTING:
    dc_channel = 1158230242452836485
    dc_area_channel = 1158582890628657213
    GUILD = 1158230241869836311
    dc_channel = None
    dc_area_channel = None
else:
    dc_channel = 1158584504965943406
    dc_area_channel = 1158589088350359553
    GUILD = 1149672933875265658

assert TOKEN

intents = discord.Intents.default()
intents.message_content = True

# logger = logging.getLogger('discord')


class MyBot(discord.ext.commands.Bot):
    async def on_ready(self):
        await self.tree.sync(guild=GUILD)


bot = MyBot(
    command_prefix="!",
    intents=intents,
    description="Squawker! Your friendly neighbord bird-bot.",
)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await bot.tree.sync(guild=discord.Object(id=GUILD))

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
    logger.info(f"Just started background_task({channel_id}, {region_code})...")
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    assert channel, f"Couldn't find channel {channel_id}"
    # await channel.send(f"Hi!  RBA Squawker reporting for duty on {region_code}!")

    logger.info(f"({channel_id}, {region_code}) ready. Getting recent posts.")
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


@bot.event
async def on_message(message):
    print(f"{message.author}: {message.channel} {message.content}")
    if message.author == bot.user:
        return

    await bot.process_commands(message)


@bot.tree.command(guild=discord.Object(id=GUILD))
async def what(ctx, code_or_name: str):
    """Look up the meaning of a 4 or 6 letter banding code or find the code for a bird by common name.

    /whats BANO
        returns Barn Owl
    /whats Barn
        returns BANO

    Parameters
    -----------
    code_or_name: str
        4 or 6 letter banding code OR part of a species common name.

    """

    return await bird_code_lookup_impl(ctx, code_or_name)


@bot.tree.command(guild=discord.Object(id=GUILD))
async def whats(ctx, code_or_name: str):
    """DEPRECATED, renamed to /what to avoid mobile autocorrect issues.
    """
    return await bird_code_lookup_impl(ctx, code_or_name)


async def bird_code_lookup_impl(ctx, code_or_name: str):
    async def respond(msg):
        await ctx.response.send_message(msg, ephemeral=True)

    input = code_or_name
    search_by_code = input.upper() == input or len(input) == 4 or len(input) == 6
    search_by_desc = input.upper() != input

    code = input.lower()
    user_desc = f"{ctx.user.name}#{ctx.user.discriminator}/{ctx.user.global_name}" if ctx.user else 'Unknown User'
    logger.info(
        f"/whats '{input}': {user_desc} {'from #' + ctx.channel.name if ctx.channel else ''}{'@' + ctx.guild.name if ctx.guild else ''}".strip()
    )
    if input == 'updog' or input == 'up dog':
        await respond("Not much, whats up with you?")
        return

    if len(code) < 3:
        msg = "Please provide at least 3 characters."
        await respond(msg)
        return

    full_response = []
    found_search_by_code = False
    if search_by_code:
        if len(code) == 6 or len(code) == 4:
            common_name = fourletter.get_common_name_by_code(code)
            if common_name:
                msg = f"`{code_or_name}` is the code for **{common_name}**."
                found_search_by_code = True
                full_response.append(msg)
        # else:
        #     msg = "Please provide a 4 or 6 letter code."
        #     full_response.append(msg)

    if search_by_desc:
        results = []
        MAX_RESULTS = 5
        for code4, comname in fourletter.code_by_common_name_substring(code, max_items=MAX_RESULTS + 1):
            msg = f"{code4} is the code for **{comname}**."
            results.append(msg)

        if results:
            msg = "\n".join(results[:MAX_RESULTS])
            if len(results) > MAX_RESULTS:
                msg += "\n...there are the first 5 results, but there are more."
            full_response.append(msg)

    if search_by_code and not found_search_by_code:
        if not full_response:
            full_response.insert(0, "I was unable to find any matches.")
        else:
            full_response.insert(
                0, "I was unable to find any bird codes that match, but you did match some bird names:"
            )

    if not full_response:
        msg = f"Sorry, I can't find any matching birds for {code_or_name}"
        full_response.append(msg)

    msg = "\n".join(full_response)
    await respond(msg)


def configure_logging():
    import logging
    import logging.handlers

    logging.getLogger('discord').setLevel(logging.INFO)
    logging.getLogger('bot').setLevel(logging.DEBUG)

    fileHandler = logging.handlers.RotatingFileHandler(
        filename='discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    fileHandler.setFormatter(formatter)

    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(discord.utils._ColourFormatter())

    rootLogger = logging.getLogger()
    rootLogger.addHandler(fileHandler)
    rootLogger.addHandler(streamHandler)


configure_logging()
bot.run(TOKEN, log_handler=None)
