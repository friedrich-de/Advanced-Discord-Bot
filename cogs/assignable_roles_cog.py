from typing import Any, Coroutine
import discord
from discord.ext import commands


class SelectRolesToAdd(discord.ui.Select):
    def __init__(self, my_guild: discord.Guild, choice_count):
        super().__init__(max_values=choice_count)
        self.guild = my_guild

    async def callback(self, interaction: discord.Interaction):
        role_ids = self.values
        role_list = [discord.utils.get(self.guild.roles, id=int(role_id)) for role_id in role_ids]
        await interaction.response.defer()
        await interaction.user.add_roles(*role_list)
        await interaction.edit_original_response(
            content=f"{interaction.user.mention} Added the following roles to you: "
            f"{', '.join([role.mention for role in role_list])}",
            view=None,
        )


class SelectRolesToRemove(discord.ui.Select):
    def __init__(self, my_guild: discord.Guild, choice_count):
        super().__init__(max_values=choice_count)
        self.guild = my_guild

    async def callback(self, interaction: discord.Interaction):
        role_ids = self.values
        role_list = [discord.utils.get(self.guild.roles, id=int(role_id)) for role_id in role_ids]
        await interaction.response.defer()
        await interaction.user.remove_roles(*role_list)
        await interaction.edit_original_response(
            content=f"{interaction.user.mention} Removed the following roles from you: "
            f"{', '.join([role.mention for role in role_list])}",
            view=None,
        )


async def load_options(interaction, assignable_roles, remove_roles=False):
    if remove_roles:
        my_role_selection = SelectRolesToRemove(interaction.guild, len(assignable_roles))
    else:
        my_role_selection = SelectRolesToAdd(interaction.guild, len(assignable_roles))
    for role_data in assignable_roles:
        role = interaction.guild.get_role(role_data["id"])
        if not role:
            continue
        my_role_selection.add_option(
            label=role.name, value=str(role_data["id"]), description=role_data["description"], emoji=role_data["emoji"]
        )
    return my_role_selection


class AssignableRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.assignable_roles = self.bot.config["assignable_roles"]["assignable"]
        self.forbidden_roles = self.bot.config["assignable_roles"]["forbidden"]

    @discord.app_commands.command(
        name="add_roles", description="Brings up the role selection menu. Add roles to yourself!"
    )
    @discord.app_commands.guild_only()
    async def add_roles(self, interaction: discord.Interaction):
        for role in interaction.user.roles:
            if role.id in self.forbidden_roles:
                await interaction.response.send_message(
                    f"{interaction.user.mention} You are not allowed to self-assign " f"roles.",
                    ephemeral=True,
                )
                return False

        view_object = discord.ui.View()
        my_role_selection = await load_options(interaction, self.assignable_roles)
        if my_role_selection:
            view_object.add_item(my_role_selection)
            await interaction.response.send_message(
                f"{interaction.user.mention} Select roles to **add** to yourself:",
                view=view_object,
                ephemeral=True,
            )

    @discord.app_commands.command(
        name="remove_roles",
        description="Brings up the role selection menu. Remove roles from yourself.",
    )
    @discord.app_commands.guild_only()
    async def remove_roles(self, interaction: discord.Interaction):
        view_object = discord.ui.View()
        my_role_selection = await load_options(interaction, self.assignable_roles, remove_roles=True)
        if my_role_selection:
            view_object.add_item(my_role_selection)
            await interaction.response.send_message(
                f"{interaction.user.mention} Select roles to **remove** from yourself:",
                view=view_object,
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(AssignableRoles(bot))
