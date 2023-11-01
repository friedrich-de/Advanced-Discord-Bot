import asyncio

import discord
from discord.ext import commands

from . import data_management
from . import utility_cog


class JoinAndLeave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.message_settings = self.bot.config["join_leave_message_settings"]
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        self.join_channel = discord.utils.get(self.guild.channels, id=self.message_settings["join_message_channel"])
        self.leave_channel = discord.utils.get(self.guild.channels, id=self.message_settings["leave_message_channel"])
        self.leave_message = self.message_settings["leave_message"]
        self.leave_message_file = self.message_settings["leave_message_file"]
        self.join_message = self.message_settings["join_message"]
        self.join_message_file = self.message_settings["join_message_file"]
        self.default_role = discord.utils.get(self.guild.roles, id=self.message_settings["default_role"])
        self.additional_message_channel = discord.utils.get(
            self.guild.channels, id=self.message_settings["additional_message_channel"]
        )
        self.additional_message = self.message_settings["additional_message"]

    @commands.Cog.listener(name="on_member_join")
    async def send_join_message(self, member: discord.Member):
        if not member.guild == self.guild:
            return

        # Main Join Message
        message = self.join_message.replace("<GUILDNAME>", member.guild.name)
        message = message.replace("<USERMENTION>", member.mention)
        message = message.replace("<USERNAME>", str(member))
        message = message.replace("<CREATIONDATE>", str(member.created_at)[0:10])
        await self.join_channel.send(message, file=discord.File(self.join_message_file))
        await member.add_roles(self.default_role)

        # Additional Message
        message = self.additional_message.replace("<GUILDNAME>", member.guild.name)
        message = message.replace("<USERMENTION>", member.mention)
        message = message.replace("<USERNAME>", str(member))
        message = message.replace("<CREATIONDATE>", str(member.created_at)[0:10])
        await self.additional_message_channel.send(message)

    @commands.Cog.listener(name="on_member_remove")
    async def send_leave_message(self, member: discord.Member):
        user_rank = await utility_cog.get_member_rank(member, self.bot)
        message = self.leave_message.replace("<RANK>", user_rank.name)
        send_file = True
        if user_rank.name == "農奴 / Unranked":
            send_file = False

        message = message.replace("<GUILDNAME>", member.guild.name)
        message = message.replace("<USERMENTION>", member.mention)
        if member.nick:
            message = message.replace("<USERNAME>", f"{str(member)} ({member.nick})")
        else:
            message = message.replace("<USERNAME>", str(member))
        if send_file:
            await self.leave_channel.send(message, file=discord.File(self.leave_message_file))
        else:
            await self.leave_channel.send(message)


async def setup(bot):
    await bot.add_cog(JoinAndLeave(bot))
