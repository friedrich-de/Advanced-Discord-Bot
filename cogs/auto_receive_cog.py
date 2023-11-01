"""Cog that enables certain roles to automatically receive other roles."""
import discord
from discord.ext import commands
from discord.ext import tasks

from . import data_management
from . import utility_cog

BANNED_FILE_NAME = "auto_receive_banned_users.yml"


class AutoReceive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.auto_receive_settings = self.bot.config["auto_receive"]
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        self.give_auto_roles.start()

    @discord.app_commands.command(
        name="ban_auto_receive", description="Ban a member from automatically receiving roles."
    )
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(
        member="The member that should be banned.", role="The role that should no longer be given."
    )
    @discord.app_commands.default_permissions(administrator=True)
    async def ban_auto_receive(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if role in member.roles:
            await member.remove_roles(role)

        banned_user_data = await data_management.load_data(BANNED_FILE_NAME)

        action = None
        banned_roles = banned_user_data.get(member.id, [])
        if banned_roles and role.id in banned_roles:
            banned_roles.remove(role.id)
            action = "Unbanned"
            banned_user_data[member.id] = banned_roles
        else:
            banned_roles.append(role.id)
            action = "Banned"
            banned_user_data[member.id] = banned_roles

        await data_management.save_data(banned_user_data, BANNED_FILE_NAME)

        await interaction.response.send_message(
            f"{action} {member} from automatically getting the role {role.name}.", ephemeral=True
        )

    @tasks.loop(minutes=10)
    async def give_auto_roles(self):
        await utility_cog.random_delay()
        banned_user_data = await data_management.load_data(BANNED_FILE_NAME)
        for role_data in self.auto_receive_settings:
            role_to_have = discord.utils.get(self.guild.roles, id=role_data["role_to_have"])
            role_to_get = discord.utils.get(self.guild.roles, id=role_data["role_to_get"])
            if not role_to_have or not role_to_get:
                continue

            banned_member_ids = [
                user_id for user_id in banned_user_data.keys() if role_to_get.id in banned_user_data[user_id]
            ]
            for member in role_to_have.members:
                if member.id in banned_member_ids:
                    print(f"AUTO-RECEIVE: Did not give {member} the role {role_to_get} due to being banned.")
                    continue

                if role_to_get not in member.roles:
                    print(f"AUTO-RECEIVE: Gave {member} the role {role_to_get}")
                    await member.add_roles(role_to_get)


async def setup(bot):
    await bot.add_cog(AutoReceive(bot))
