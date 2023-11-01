import discord
from discord.ext import commands
from discord.ext import tasks

from datetime import datetime
import asyncio
import yaml
import os
import glob


async def snapshot_autocomplete(interaction: discord.Interaction, current_input: str):
    folder_path = "data/snapshot_data"

    # Using glob to get all .yml files in subdirectories
    snapshots = glob.glob(os.path.join(folder_path, "*", "*.yml"))

    possible_choices = [
        discord.app_commands.Choice(name=os.path.basename(snapshot), value=snapshot)
        for snapshot in snapshots
        if current_input in os.path.basename(snapshot)
    ]

    return possible_choices[:25]


async def check_if_top_role(guild, bot):
    top_role = None
    for role in guild.roles:
        if not top_role:
            top_role = role
        if top_role < role:
            top_role = role

    bot_member = guild.get_member(bot.user.id)
    if top_role not in bot_member.roles:
        return False
    else:
        for role in bot_member.roles:
            if role.is_bot_managed():
                return role


async def delete_roles(guild: discord.Guild):
    for role in guild.roles:
        try:
            await asyncio.sleep(1)
            print(f"Deleting role: {role.name}")
            await role.delete(reason="Restoration.")
        except discord.errors.HTTPException:
            print(f"Failed to delete role: {role.name}")


async def delete_all_channels(guild: discord.Guild):
    for channel in guild.channels:
        await asyncio.sleep(1)
        print(f"Deleting channel: {channel.name}")
        await channel.delete()


class ConfirmDeletionButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="I am sure.", style=discord.ButtonStyle.danger)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Deleting guild...")
        await delete_roles(interaction.guild)
        await delete_all_channels(interaction.guild)
        await interaction.guild.create_text_channel("temp")
        await interaction.guild.text_channels[0].send("Finished deleting guild.")


async def create_normal_roles(guild: discord.Guild, snapshot_data: dict, bot_role: discord.Role):
    for role in snapshot_data["roles"]:
        if role["name"] == "@everyone":
            print("SNAPSHOT LOADER: Editing @everyone role.")
            if guild.default_role.permissions.value != discord.Permissions(role["permissions"]):
                await guild.default_role.edit(
                    permissions=discord.Permissions(role["permissions"]),
                    reason="Restoration.",
                )
                continue

        elif role["name"] == "Server Booster":
            continue

        await asyncio.sleep(2)

        if role["name"] not in [role.name for role in guild.roles]:
            print(f"SNAPSHOT LOADER: Creating role: {role['name']}")
            await guild.create_role(
                name=role["name"],
                color=discord.Color(role["color"]),
                hoist=role["hoist"],
                mentionable=role["mentionable"],
                permissions=discord.Permissions(role["permissions"]),
                reason="Restoration.",
            )
        else:
            print(f"SNAPSHOT LOADER: Skipping role: {role['name']} as it already exists.")

    print("SNAPSHOT LOADER: Trying to edit role positions now.")
    positions_dict = dict()
    for role in snapshot_data["roles"]:
        role_position = role["position"]
        server_role = discord.utils.get(guild.roles, name=role["name"])
        if not server_role:
            print(f"SNAPSHOT LOADER: Role {role['name']} not found.")
            continue
        positions_dict[server_role] = role_position

    highest_value = max(positions_dict.values())
    positions_dict[bot_role] = highest_value + 1

    print("SNAPSHOT LOADER: Editing role positions.")
    await guild.edit_role_positions(positions_dict, reason="Restoration.")


async def create_category_channels(guild: discord.Guild, snapshot_data: dict):
    for channel in snapshot_data["channels"]:
        if channel["type"] == 4:
            await asyncio.sleep(2)
            print(f"SNAPSHOT LOADER: Creating category: {channel['name']}")
            category_channel = await guild.create_category(
                name=channel["name"],
                position=channel["position"],
                reason="Restoration.",
            )
        else:
            continue

        overwrites = channel["overwrites"]
        for overwrite in overwrites:
            if overwrite["type"] == "role":
                overwrite_target = discord.utils.get(guild.roles, name=overwrite["role_name"])
            elif overwrite["type"] == "user":
                overwrite_target = guild.get_member(overwrite["target_id"])
            if not overwrite_target:
                continue

            overwrite_permissions = discord.PermissionOverwrite(**overwrite["permissions"])

            await asyncio.sleep(5)
            print(
                f"SNAPSHOT LOADER: Setting channel permissions for {overwrite_target.name} "
                f"in channel {channel['name']}"
            )
            await category_channel.set_permissions(
                overwrite_target,
                overwrite=overwrite_permissions,
                reason="Restoration.",
            )


async def create_normal_channels(guild: discord.Guild, snapshot_data: dict):
    for channel in snapshot_data["channels"]:
        if channel["type"] == 4:
            continue

        await asyncio.sleep(2)
        print(f"SNAPSHOT LOADER: Creating channel: {channel['name']}")
        category = discord.utils.get(guild.categories, name=channel["category"])
        if channel["type"] == 0:
            new_channel = await guild.create_text_channel(
                name=channel["name"],
                position=channel["position"],
                topic=channel["topic"],
                nsfw=channel["nsfw"],
                reason="Restoration.",
                category=category,
            )
        elif channel["type"] == 2:
            new_channel = await guild.create_voice_channel(
                name=channel["name"], position=channel["position"], reason="Restoration.", category=category
            )

        overwrites = channel["overwrites"]
        for overwrite in overwrites:
            if overwrite["type"] == "role":
                overwrite_target = discord.utils.get(guild.roles, name=overwrite["role_name"])
            elif overwrite["type"] == "user":
                overwrite_target = guild.get_member(overwrite["target_id"])
            if not overwrite_target:
                continue

            overwrite_permissions = discord.PermissionOverwrite(**overwrite["permissions"])

            await asyncio.sleep(5)
            print(
                f"SNAPSHOT LOADER: Setting channel permissions for {overwrite_target.name} "
                f"in channel {channel['name']}"
            )
            await new_channel.set_permissions(
                overwrite_target,
                overwrite=overwrite_permissions,
                reason="Restoration.",
            )


async def create_threads(guild: discord.Guild, snapshot_data: dict):
    for thread in snapshot_data["threads"]:
        await asyncio.sleep(2)
        print(f"SNAPSHOT LOADER: Creating thread: {thread['name']}")
        channel = discord.utils.get(guild.channels, name=thread["parent_channel_name"])
        thread_channel = await channel.create_thread(
            name=thread["name"],
            auto_archive_duration=thread["auto_archive_duration"],
            reason="Restoration.",
        )

        if thread["archived"]:
            print(f"SNAPSHOT LOADER: Archiving thread: {thread['name']}")
            await thread_channel.edit(archived=True)


async def create_pins(guild: discord.Guild, snapshot_data: dict):
    for pin in snapshot_data["pins"]:
        channel = discord.utils.get(guild.channels, name=pin["channel_name"])
        message_content = f"**Pinned messaged by {pin['author_name']} on {pin['date']}**\n\n{pin['message_content']}"
        files = [discord.File(file_path) for file_path in pin["attachments"]]

        await asyncio.sleep(5)
        print(f"SNAPSHOT LOADER: Sending message by {pin['author_name']} in channel {pin['channel_name']}")
        message = await channel.send(
            content=message_content, allowed_mentions=discord.AllowedMentions.none(), files=files
        )

        await asyncio.sleep(1)
        print(f"SNAPSHOT LOADER: Pinning message by {pin['author_name']} in channel {pin['channel_name']}")
        await message.pin()


class StateLoader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="_delete_server", description="Delete all server data.")
    @discord.app_commands.guild_only()
    @discord.app_commands.default_permissions(administrator=True)
    async def delete_server(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        bot_role = await check_if_top_role(interaction.guild, self.bot)
        if not bot_role:
            await interaction.edit_original_response(content="Bot role has to be top role!")
            return

        button_view = discord.ui.View()
        button_view.add_item(ConfirmDeletionButton(self.bot))

        channel_mentions = " | ".join([channel.mention for channel in interaction.guild.channels])
        role_mentions = " | ".join([role.mention for role in interaction.guild.roles if not role.is_bot_managed()])
        to_delete_embed = discord.Embed(
            title="Roles and Channels to delete:",
            description=f"**Channels**: {channel_mentions}\n\n" f"**Roles** {role_mentions}",
        )

        await interaction.edit_original_response(
            content=f"Are you sure you want to load the snapshot?\n **THIS WILL DELETE ALL ROLES AND CHANNELS.**",
            embed=to_delete_embed,
            view=button_view,
        )

    @discord.app_commands.command(name="_load_snapshot", description="Load a snapshot and create server.")
    @discord.app_commands.guild_only()
    @discord.app_commands.autocomplete(file_path=snapshot_autocomplete)
    @discord.app_commands.default_permissions(administrator=True)
    async def load_snapshot(self, interaction: discord.Interaction, file_path: str):
        await interaction.response.defer()
        with open(file_path, "r") as snapshot_file:
            snapshot_data = yaml.safe_load(snapshot_file)

        bot_role = await check_if_top_role(interaction.guild, self.bot)
        if not bot_role:
            await interaction.edit_original_response(content="Bot role has to be top role!")
            return

        print(f"SNAPSHOT LOADER: Loading snapshot: {snapshot_data['name']}")

        print("SNAPSHOT LOADER: Creating roles.")
        await create_normal_roles(interaction.guild, snapshot_data, bot_role)
        print("SNAPSHOT LOADER: Finished creating roles.")

        print("SNAPSHOT LOADER: Creating categories.")
        await create_category_channels(interaction.guild, snapshot_data)
        print("SNAPSHOT LOADER: Finished creating categories.")

        print("SNAPSHOT LOADER: Creating channels.")
        await create_normal_channels(interaction.guild, snapshot_data)
        print("SNAPSHOT LOADER: Finished creating channels.")

        print("SNAPSHOT LOADER: Creating threads.")
        await create_threads(interaction.guild, snapshot_data)
        print("SNAPSHOT LOADER: Finished creating threads.")

        print("SNAPSHOT LOADER: Creating pins.")
        await create_pins(interaction.guild, snapshot_data)
        print("SNAPSHOT LOADER: Finished creating pins.")

        await interaction.edit_original_response(content="Finished loading snapshot.")


async def setup(bot):
    await bot.add_cog(StateLoader(bot))
