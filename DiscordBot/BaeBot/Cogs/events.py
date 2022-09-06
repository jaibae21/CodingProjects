######################################################################################
# Author: Jaiden
# Notes: Handles join/leave, bot chatting, general error handling
######################################################################################
from discord.ext import commands

class Events(commands.Cog):

	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		print('Events loaded.')

	@commands.Cog.listener()
	async def on_member_join(self, member):
		print(f'(member) has joined the server')

	@commands.Cog.listener()
	async def on_member_remove(self, member):
		print(f'(member) has joined the server')

	@commands.Cog.listener()
	async def on_command_error(self, ctx, error):
		if isinstance(error, commands.CommandNotFound):
			await ctx.send("Command doesn't exist.")
		if isinstance(error, commands.MissingPermissions):
			await ctx.send("You don't have permission to use this command.")
	#causes duplicate response when clear command is used
	#	#handles all Missing Requirement errors
	#	if isinstance(error, commands.MissingRequiredArgument):
	#		await ctx.send('Please pass in all required arguments.')

	@commands.Cog.listener()
	async def on_message(self, message):
		if message.author == self.bot.user:
			return
		greetings = ['Hello', 'Hi', 'hello', 'hi']
		farewells = ['Bye', 'Goodbye', 'See ya', 'bye', 'goodbye']
		if any([keyword in message.content for keyword in (greetings)]):
			await message.channel.send(f'Hi {message.author.display_name}') #display_name to show nickname instead of username
		if any([keyword in message.content for keyword in (farewells)]):
			await message.channel.send(f'Goodbye {message.author.display_name}')
		
#Causes duplicate responses
#await self.bot.process_commands(message)    #prevents ping command from running

def setup(bot):
	bot.add_cog(Events(bot))