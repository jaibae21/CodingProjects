######################################################################################
# Author: Jaiden
# Notes: 
######################################################################################
import discord
from discord.ext import commands
import random

class Fun(commands.Cog):

	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		print('Fun commands loaded.')

	@commands.command(aliases=['8ball'])
	async def _8ball(self, ctx, *, question):
		responses = ['It is certain', 'It is decidely so.', 'Without a doubt', 'Yes - definitely.', 'You may rely on it', 'As I see it, yes', 'Most likely', 'Outlook good.', 'Yes.', 'Signs point to yes.', 'Reply hazy, try again.', 'Ask again later.', 'Better not tell you now.', 'Cannot predict now.', 'Concentrate and ask again', "Don't count on it.", 'My reply is no', 'My sources say no', 'Outlook not so good', 'Very doubtful.']
		await ctx.send(f'Question: {question}\nAnswer: {random.choice(responses)}')
	
	@commands.command()
	async def ping(self, ctx):
		await ctx.send(f'Pong! {round(self.bot.latency * 1000)} ms')

	@commands.command()
	async def coinflip(self, ctx):
		outcome = ['head', 'tails']
		await ctx.send(f'{random.choice(outcome)}')

	@commands.command()
	async def dice(self, ctx):
		outcome = ['1', '2', '3', '4', '5', '6']
		await ctx.send(f'You rollded a {random.choice(outcome)}')

def setup(bot):
	bot.add_cog(Fun(bot))