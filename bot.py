# This example requires the 'message_content' intent.

import time
import discord
import os
from dotenv import load_dotenv

import ebird

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


import requests


@client.event
async def on_message(message):
    print(message.author, client.user, message.content)
    if message.author == client.user:
        return

    url = 'https://api.ebird.org/v2/data/obs/US-DC/recent/notable?back=1&detail=full'

    for msg in ebird.get_rare_text():
        await message.channel.send(msg)
        time.sleep(1.0)
    # if message.content.startswith('$hello'):
    # await message.channel.send('Hello!')


client.run(TOKEN)
