######################################################################################
# Author: Jaiden
# Notes: commands.Bot is an extension of discord.Client()
######################################################################################

import os, io, discord, logging, random, json
from itertools import cycle
from discord.ext import commands, tasks

TOKEN = "OTI5NTI1NTA3MDk0MDkzODI0.YdomFg.WxbG7wagLqJtJMZlJetm_z3JTQM"

status = cycle(["Creating Bae's for your server.", 'Loafs being made'])

def get_prefix(bot, message):
	with open('prefixes.json', 'r') as f:
		prefixes = json.load(f)

	return prefixes[str(message.guild.id)]

bot = commands.Bot(command_prefix=get_prefix)	#must be towards top of code

##Simple logging
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8',mode='w')
handler.setFormatter(logging.Formatter('%asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

##Custom Check
#allows only a certain user to use a command
def is_it_me(ctx):
	return ctx.author.id == 589626884166254612

##Tasks
#update bot status every interval
@tasks.loop(seconds=60)
async def change_status():
	await bot.change_presence(activity=discord.Game(next(status)))

##Events
#bot is up
@bot.event
async def on_ready():
	#Bot Status
	await bot.change_presence(status=discord.Status.online)
	change_status.start()
	print(f'{bot.user} successfully logged in!')

@bot.event
async def on_guild_join(guild):
	with open('prefixes.json', 'r') as f:
		prefixes = json.load(f)

	prefixes[str(guild.id)] = '*'	#default before they change it

	with open('prefixes.json', 'w') as f:
		json.dump(prefixes, f, indent=4)

@bot.event
async def on_guild_remove(guild):
	with open('prefixes.json', 'r') as f:
		prefixes = json.load(f)

	prefixes.pop(str(guild.id))

	with open('prefixes.json', 'w') as f:
		json.dump(prefixes, f, indent=4)

##Commands
#Clear messages
@bot.command(aliases=['clear'])
@commands.check(is_it_me)
async def clearMsg(ctx, amount : int):
	await ctx.channel.purge(limit=amount)   #take context, find channel running, purge method

#change prefix
@bot.command(hidden=True)
@commands.has_permissions(administrator=True)
async def changeprefix(ctx,prefix):
	with open('prefixes.json', 'r') as f:
		prefixes = json.load(f)

	prefixes[str(ctx.guild.id)] = prefix	#default before they change it

	with open('prefixes.json', 'w') as f:
		json.dump(prefixes, f, indent=4)

#function specific error handling
@clearMsg.error	
async def clear_error(ctx, error):
	if isinstance(error, commands.MissingRequiredArgument):
		await ctx.send('Please specify amount of msgs to delete.')

##Cogs
@bot.command(hidden=True)
async def load(ctx, extension):	#extension is the cog you want to load
	bot.load_extension(f'Cogs.{extension}')	#the Cogs part follows whatever you name the folder

@bot.command(hidden=True)
async def unload(ctx, extension):	#extension is the cog you want to load
	bot.unload_extension(f'Cogs.{extension}')

@bot.command(hidden=True)
async def reload(ctx, extension):
	bot.unload_extension(f'Cogs.{extension}')
	bot.load_extension(f'Cogs.{extension}')

for filename in os.listdir('./Cogs'):
	if filename.endswith('.py'):
		bot.load_extension(f'Cogs.{filename[:-3]}')	#cut off .py part from filename

bot.run(TOKEN)