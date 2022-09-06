######################################################################################
# Author: Jaiden
# Notes: Commands here have not been tested
######################################################################################

import discord
import asyncio
from discord.ext import commands

class DurationConverter(commands.Converter):
	async def convert(self, ctx, argument):
		amount = argument[:-1]
		unit = argument[-1]
		
		if amount.isdigit() and unit in ['s', 'm']:
			return (int(amount), unit)
		
		raise commands.BadArgument(message='Not a valid duration')

class Admin(commands.Cog):

	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		print('Admin commands ready.')


	#Ban
	@commands.command()
	@commands.has_permissions(administrator=True)
	#using converters
	async def ban(ctx, member: commands.MemberConverter):	#gives different lookup methods
		await ctx.guild.ban(member)
		await ctx.send(f'{member} has been banned')
	# #needs actual mention of user
	#async def ban(self, ctx, member : discord.Member, *,reason=None):
	#	await member.ban(reason=reason)

	@commands.command()
	@commands.has_permissions(administrator=True)
	#using custom converters
	async def tempban(ctx, member: commands.MemberConverter, duration: DurationConverter):	
		multipier = {'s' : 1, 'm': 60}
		amount, unit = duration
		await ctx.guild.ban(member)
		await ctx.send(f'{member} has been banned for {amount}{unit}')
		await asyncio.sleep(amount * multiplie[unit])
		await ctx.guild.unban(member)
	# #needs actual mention of user
	#async def ban(self, ctx, member : discord.Member, *,reason=None):
	#	await member.ban(reason=reason)

	#Kick
	@commands.command()
	@commands.has_permissions(administrator=True)
	async def kick(self, ctx, member : discord.Member, *,reason=None):    #pass the person as a mention so you can pull up their profile info after kicking
		await member.kick(reason=reason)

	@commands.command()
	@commands.has_permissions(administrator=True)
	async def unban(ctx, *, member):   #not in server so we can't mention them, * important bc some names have spaces in them
		banned_users = await ctx.guild.bans()   #get list of banned entries
		member_name, member_discriminator = member.split('#')   #split member into name and discriminator
		for ban_entry in banned_users:
			user = ban_entry.user

			if (user.name, user.discriminator) == (member_name, member_discriminator):
					await ctx.guild.unban(user)
					await ctx.send(f'Unbanned {user.mention}')
					return

def setup(bot):
	bot.add_cog(Admin(bot))