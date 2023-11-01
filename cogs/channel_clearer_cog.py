import discord
from discord.ext import commands
from discord.ext import tasks

from . import utility_cog

from datetime import datetime
from datetime import timedelta


class ChannelClearer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await self.bot.wait_until_ready()
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])

        clear_channel_ids = self.bot.config["channels_to_clear"]
        self.clear_channels = []
        for channel_id in clear_channel_ids:
            channel = self.guild.get_channel(channel_id)
            if channel:
                self.clear_channels.append(channel)

        self.channel_clearer.start()

    @tasks.loop(minutes=60)
    async def channel_clearer(self):
        await utility_cog.random_delay()

        def check_if_pin(msg: discord.Message):
            if msg.pinned:
                return False
            else:
                return True

        for channel in self.clear_channels:
            now = datetime.utcnow()
            two_weeks = timedelta(days=13)
            one_day = timedelta(hours=24)
            print(f"CLEARER: Purging channel '{channel.name}'.")
            purged_message = await channel.purge(
                limit=None, check=check_if_pin, oldest_first=True, before=now - one_day, after=now - two_weeks
            )
            print(f"CLEARER: Purged {len(purged_message)} messages from '{channel.name}'.")


async def setup(bot):
    await bot.add_cog(ChannelClearer(bot))
