import discord
from discord.ext import commands
from discord.ext import tasks
import ast

from . import data_management
from . import utility_cog


FILE_NAME = "user_names.yml"
USER_NAME_DICTIONARY = dict()
DATA_LOADED = False


async def load_data():
    global USER_NAME_DICTIONARY
    USER_NAME_DICTIONARY = await data_management.load_data(FILE_NAME)
    global DATA_LOADED
    DATA_LOADED = True


async def get_user_name(bot, user_id):
    if not DATA_LOADED:
        await load_data()
    user_name = USER_NAME_DICTIONARY.get(user_id)
    if not user_name:
        print(f"USERNAMES: Unable to find user with ID {user_id}. Attempting to fetch username...")
        try:
            user = await bot.fetch_user(user_id)
            if user:
                user_name = str(user)
            else:
                user_name = "<unknown-user>"
        except discord.errors.NotFound:
            user_name = "<unknown-user>"
        print(f"USERNAMES: Saving user name for {user_id} as {user_name}")
        await add_user_name(user_id, user_name)
    try:
        user_name = ast.literal_eval(user_name)
    except ValueError:
        pass
    return user_name


async def add_user_name(user_id, user_name):
    global USER_NAME_DICTIONARY
    USER_NAME_DICTIONARY[user_id] = user_name
    await data_management.save_data(USER_NAME_DICTIONARY, FILE_NAME)


class UsernameStorage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await self.bot.wait_until_ready()
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        self.save_and_load_user_names.start()

    @tasks.loop(hours=24)
    async def save_and_load_user_names(self):
        await utility_cog.random_delay()
        global USER_NAME_DICTIONARY
        if not DATA_LOADED:
            await load_data()
        for member in self.guild.members:
            USER_NAME_DICTIONARY[member.id] = member.name
        await data_management.save_data(USER_NAME_DICTIONARY, FILE_NAME)
        print("USERNAMES: Saved and loaded user names.")


async def setup(bot):
    await bot.add_cog(UsernameStorage(bot))
