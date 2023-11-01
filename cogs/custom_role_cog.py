import discord
from discord.ext import commands
from discord.ext import tasks

import re
import asyncio

from . import data_management
from . import utility_cog

CUSTOM_ROLE_FILE_NAME = "custom_role_data.yml"


async def clear_custom_role_data(member: discord.Member):
    custom_role_data = await data_management.load_data(CUSTOM_ROLE_FILE_NAME)
    if member.id in custom_role_data:
        role_id = custom_role_data.get(member.id)
        custom_role = member.guild.get_role(role_id)
        if custom_role:
            await custom_role.delete()
        del custom_role_data[member.id]
        await data_management.save_data(custom_role_data, CUSTOM_ROLE_FILE_NAME)
    return custom_role_data


class CustomRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await self.bot.wait_until_ready()
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        self.allowed_role_ids = self.bot.config["custom_roles"]["allowed_roles"]
        self.reference_role = self.guild.get_role(self.bot.config["custom_roles"]["reference_role"])
        self.strip_roles.start()

    async def check_if_allowed(self, member: discord.Member):
        for role in member.roles:
            if role.id in self.allowed_role_ids:
                return True
        return False

    @discord.app_commands.command(name="make_custom_role", description="Create a custom role for yourself.")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(
        role_name="Role name. Maximum of 7 symbols.",
        color_code="Hex color code. Example: #A47267",
        role_icon="Image that should be used.",
    )
    async def make_custom_role(
        self, interaction: discord.Interaction, role_name: str, color_code: str, role_icon: discord.Attachment = None
    ):
        await interaction.response.defer()

        allowed = await self.check_if_allowed(interaction.user)
        if not allowed:
            await interaction.edit_original_response(content="You are not allowed to create a custom role.")
            return

        if len(role_name) > 7:
            await interaction.edit_original_response(
                content="Please use a shorter role name. Restrict yourself to 7 symbols."
            )
            return

        color_match = re.search(r"^#(?:[0-9a-fA-F]{3}){1,2}$", color_code)
        if not color_match:
            await interaction.edit_original_response(
                content="Please enter a valid hex color code. Example: `#A47267` "
            )
            return

        custom_role_data = await data_management.load_data(CUSTOM_ROLE_FILE_NAME)
        if interaction.user.id in custom_role_data:
            await clear_custom_role_data(interaction.user)

        if role_name in [role.name for role in interaction.guild.roles]:
            await interaction.edit_original_response(content="You can't use this role name.")
            return

        actual_color_code = int(re.findall(r"^#((?:[0-9a-fA-F]{3}){1,2})$", color_code)[0], base=16)
        discord_colour = discord.Colour(actual_color_code)

        if role_icon:
            display_icon = await role_icon.read()
            custom_role = await interaction.guild.create_role(
                name=role_name, colour=discord_colour, display_icon=display_icon
            )
        else:
            custom_role = await interaction.guild.create_role(name=role_name, colour=discord_colour)

        positions = {custom_role: self.reference_role.position + 1}
        await interaction.guild.edit_role_positions(positions)
        await interaction.user.add_roles(custom_role)

        custom_role_data[interaction.user.id] = custom_role.id
        await data_management.save_data(custom_role_data, CUSTOM_ROLE_FILE_NAME)
        await interaction.edit_original_response(content=f"Created your custom role: {custom_role.mention}")

    @discord.app_commands.command(name="delete_custom_role", description="Remove a custom role from yourself.")
    @discord.app_commands.guild_only()
    async def delete_custom_role(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await clear_custom_role_data(interaction.user)
        await interaction.edit_original_response(content="Deleted your custom role.")

    @tasks.loop(minutes=200)
    async def strip_roles(self):
        await utility_cog.random_delay()
        custom_role_data = await data_management.load_data(CUSTOM_ROLE_FILE_NAME)
        for member_id in custom_role_data:
            member = self.guild.get_member(member_id)
            if member:
                if set([role.id for role in member.roles]) & set(self.allowed_role_ids):
                    custom_role_allowed = True
                else:
                    custom_role_allowed = False
                if not custom_role_allowed:
                    await asyncio.sleep(5)
                    await clear_custom_role_data(member)
                    print(f"CUSTOM ROLE: Removed custom role from {str(member)}.")
            else:
                new_custom_role_data = await data_management.load_data(CUSTOM_ROLE_FILE_NAME)
                role = self.guild.get_role(custom_role_data[member_id])
                if role:
                    await role.delete()
                del new_custom_role_data[member_id]
                await data_management.save_data(new_custom_role_data, CUSTOM_ROLE_FILE_NAME)


async def setup(bot):
    await bot.add_cog(CustomRole(bot))
