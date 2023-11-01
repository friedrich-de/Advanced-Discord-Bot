"""Create a temporary voice channel"""
import asyncio

import discord
from discord.ext import commands
from discord.ext import tasks

from . import data_management
from . import utility_cog

#########################################

TEMPORARY_VC_FILE_NAME = "temporary_vcs.yml"


class TemporaryVC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        self.clear_vcs.start()

    async def cog_unload(self):
        self.clear_vcs.cancel()

    @discord.app_commands.command(
        name="create_vc", description="Create a temporary voice channel. Need to be inside a VC to use this command!"
    )
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(channel_name="The name of the temporary voice channel.")
    @discord.app_commands.default_permissions(send_messages=True)
    async def create_vc(self, interaction: discord.Interaction, channel_name: str):
        if interaction.user.voice:
            bottom_vc = interaction.guild.voice_channels[-1]
            custom_vc = await interaction.guild.create_voice_channel(
                name=channel_name, reason="User command", category=bottom_vc.category, position=bottom_vc.position + 1
            )

            await interaction.user.move_to(custom_vc, reason="Channel creation.")
            custom_vc_list = await data_management.load_data(TEMPORARY_VC_FILE_NAME, return_list=True)
            custom_vc_list.append(custom_vc.id)
            await data_management.save_data(custom_vc_list, TEMPORARY_VC_FILE_NAME)
            await interaction.response.send_message(f"Created a temporary voice channel called `{channel_name}`.")
        else:
            await interaction.response.send_message(
                "You need to be in a voice channel to use this command.", ephemeral=True
            )
            return

    @tasks.loop(minutes=5)
    async def clear_vcs(self):
        await utility_cog.random_delay()
        custom_vc_list = await data_management.load_data(TEMPORARY_VC_FILE_NAME, return_list=True)
        for custom_vc_id in custom_vc_list:
            custom_vc = self.guild.get_channel(custom_vc_id)
            if not custom_vc:
                custom_vc_list.remove(custom_vc_id)
                await data_management.save_data(custom_vc_list, TEMPORARY_VC_FILE_NAME)
            if not custom_vc.members:
                await custom_vc.delete(reason="Empty custom channel.")
                custom_vc_list.remove(custom_vc_id)
                await data_management.save_data(custom_vc_list, TEMPORARY_VC_FILE_NAME)


async def setup(bot):
    await bot.add_cog(TemporaryVC(bot))
