"""Backup role data"""
import asyncio

import discord
from discord.ext import commands
from discord.ext import tasks

from . import data_management
from . import utility_cog

USER_RANKS_FILE_NAME = "user_ranks.yaml"


async def load_user_ranks():
    return await data_management.load_data(USER_RANKS_FILE_NAME)


async def save_user_ranks(user_ranks):
    await data_management.save_data(user_ranks, USER_RANKS_FILE_NAME)


class RankSaver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        role_ids_to_save = self.bot.config["rank_hierarchy"][:-1]
        self.role_names_to_save = [
            discord.utils.get(self.guild.roles, id=role_id).name for role_id in role_ids_to_save
        ]
        self.rank_saver.start()

    @tasks.loop(minutes=10.0)
    async def rank_saver(self):
        await utility_cog.random_delay()
        print("RANK SAVER: Saving ranks.")
        user_role_data = await load_user_ranks()
        all_members = [member for member in self.guild.members if member.bot is False]
        for member in all_members:
            member_role_names = [role.name for role in member.roles if role.name in self.role_names_to_save]
            user_role_data[member.id] = member_role_names

        for user_id in list(user_role_data.keys()):
            user_roles = [role_name for role_name in user_role_data[user_id] if role_name in self.role_names_to_save]
            if not user_roles == user_role_data[user_id]:
                user_role_data[user_id] = user_roles
            if not user_roles:
                del user_role_data[user_id]

        await save_user_ranks(user_role_data)

    @commands.Cog.listener(name="on_member_join")
    async def rank_restorer(self, member: discord.Member):
        user_role_data = await load_user_ranks()
        role_names = user_role_data.get(member.id, [])
        if role_names:
            print(f"RANK SAVER: Restoring roles for {member.name}.")
            await asyncio.sleep(10)
            roles_to_restore = [discord.utils.get(member.guild.roles, name=role_name) for role_name in role_names]
            role_to_remove = self.guild.get_role(self.bot.config["join_leave_message_settings"]["default_role"])
            await member.remove_roles(role_to_remove)
            await member.add_roles(*roles_to_restore)
        else:
            return
        to_restore_channel = self.guild.get_channel(self.bot.config["rank_system"]["success_announce_channel"])
        await to_restore_channel.send(
            f"Restored **{', '.join([role.name for role in roles_to_restore])}** for" f"{member.mention}."
        )


async def setup(bot):
    await bot.add_cog(RankSaver(bot))
