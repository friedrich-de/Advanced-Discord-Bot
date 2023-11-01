import os
import discord
import yaml

from discord.ext import commands

TESTING_MODE = False
TESTING_COGS = ["cogs.nickname_counter_cog"]
TESTING_PREFIX = "$"


class PersonalBot(commands.Bot):
    def __init__(self):
        with open("settings.yml") as config_file:
            self.config = yaml.safe_load(config_file)

        if not TESTING_MODE:
            command_prefix = self.config["bot"]["command_prefix"]
        else:
            command_prefix = TESTING_PREFIX

        super().__init__(command_prefix=command_prefix, intents=discord.Intents.all())

        if not TESTING_MODE:
            with open("data/token.txt") as token_file:
                self.token = token_file.read()
        else:
            with open("data/test_token.txt") as token_file:
                self.token = token_file.read()

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        await self.load_cogs()

    async def load_cogs(self):
        cog_folder = "cogs"

        if not TESTING_MODE:
            cogs = [cog for cog in os.listdir(cog_folder) if cog.endswith(".py") and "cog" in cog]
            for cog in cogs:
                cog = f"{cog_folder}.{cog[:-3]}"
                await self.load_extension(cog)
                print(f"Loaded {cog}")
        else:
            await self.load_extension("cogs.utility_cog")
            print("Loaded cogs.utility_cog")
            for TESTING_COG in TESTING_COGS:
                await self.load_extension(TESTING_COG)
                print(f"Loaded {TESTING_COG}")


my_bot = PersonalBot()
my_bot.run(my_bot.token)
