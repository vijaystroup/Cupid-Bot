# IMPORTS
from cupid_token import token
import discord
from discord.ext import commands
import logging
from logging.handlers import RotatingFileHandler
from logging import debug, info, warning, error, critical
from os import listdir, getenv
import sys, signal
import dbconnection as db

# set up logging
cupid_base = getenv('CUPID_BASE')
log = logging.getLogger('discord')
log.setLevel(logging.INFO)
handler = RotatingFileHandler(f'{cupid_base}/logs/discord.log', mode='a',
    maxBytes=1024*1024, backupCount=3, encoding='utf-8', delay=0)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
log.addHandler(handler)
log.info('Starting...')

# set token and initalize client
TOKEN = token()
client = commands.Bot(command_prefix = '.')

# remove default help command so the custom one may be implemented
client.remove_command('help')

# ON_READY
@client.event
async def on_ready():
    log.info('on_ready')
    # load in all extensions
    for filename in listdir('./cogs'):
        if filename.endswith('.py'):
            client.load_extension(f'cogs.{filename[:-3]}')

    # connect to database
    log.info('connecting to database..')

    # change bot status
    await client.change_presence(activity=discord.Game(f'.help @{client.user}'))

    # console message letting us know everything is ready
    log.info(f'**{client.user} is ready**') # "Bot#1234 is ready"


# LOAD_EXTENSION CMD
@client.command()
async def load(ctx, extension):
    if ctx.message.author.id == 168445919031853056:
        client.load_extension(f'cogs.{extension}')
    return

# UNLOAD_EXTENSION CMD
@client.command()
async def unload(ctx, extension):
    if ctx.message.author.id == 168445919031853056:
        client.unload_extension(f'cogs.{extension}')
    return

# RELOAD_EXTENSION CMD
@client.command()
async def reload(ctx, extension):
    if ctx.message.author.id == 168445919031853056:
        client.unload_extension(f'cogs.{extension}')
        client.load_extension(f'cogs.{extension}')
    return

# SHUTDOWN CMD
@client.command()
async def shutdown(ctx):
    if ctx.message.author.id == 168445919031853056:
        log.info('Closing db connection.')
        db.conn.close()
        log.info('Closing discord client connection.')
        await client.close()
        log.info('Exiting.')
        sys.exit(0)
        return
    return

if __name__ == '__main__':
    client.run(TOKEN)

