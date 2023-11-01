import discord
from discord.ext import commands
from discord.ext import tasks

from datetime import datetime
import asyncio
import yaml
import os
import time


async def save_role_display_icon(role: discord.Role):
    icon_asset = role.display_icon
    file_path = f"data/snapshot_data/{role.guild.id}/{role.id}_icon.png"
    print("STATE SAVER: Saving icon for role: " + role.name + " to " + file_path)
    try:
        with open(file_path):
            print("STATE SAVER: Display icon already exists.")
    except FileNotFoundError:
        await asyncio.sleep(5)
        await icon_asset.save(file_path)
    return file_path


async def save_user_role_data_to_snapshot(guild: discord.Guild, snapshot_data: dict):
    role_data = list()
    for role in guild.roles:
        if role.is_bot_managed():
            continue

        if not role.display_icon:
            role_icon = False
        else:
            role_icon = await save_role_display_icon(role)

        role_data.append(
            {
                "name": role.name,
                "id": role.id,
                "color": role.color.value,
                "permissions": role.permissions.value,
                "position": role.position,
                "mentionable": role.mentionable,
                "hoist": role.hoist,
                "icon": role_icon,
            }
        )
    snapshot_data["roles"] = role_data


async def get_channel_override_data(channel: discord.abc.GuildChannel):
    overwrites = list()
    for role_or_user, permission_overwrite in channel.overwrites.items():
        current_overwrite = dict()
        if isinstance(role_or_user, discord.Role):
            overwrite_type = "role"
            role_name = role_or_user.name
        elif isinstance(role_or_user, discord.User):
            overwrite_type = "user"
            role_name = None
        overwrite_target_id = role_or_user.id
        for perm, value in iter(permission_overwrite):
            if value is None:
                continue
            current_overwrite[perm] = value
        overwrites.append(
            {
                "type": overwrite_type,
                "target_id": overwrite_target_id,
                "role_name": role_name,
                "permissions": current_overwrite,
            }
        )
    return overwrites


async def save_channel_data_to_snapshot(guild: discord.Guild, snapshot_data: dict):
    channel_data = list()
    for channel in guild.channels:
        try:
            topic = channel.topic
        except AttributeError:
            topic = None

        print("STATE SAVER: Saving channel: " + channel.name)
        channel_data.append(
            {
                "name": channel.name,
                "channel_id": channel.id,
                "type": channel.type.value,
                "position": channel.position,
                "category": channel.category.name if channel.category else None,
                "topic": topic,
                "nsfw": channel.is_nsfw(),
                "sync_permissions": channel.permissions_synced,
                "overwrites": await get_channel_override_data(channel),
            }
        )
    snapshot_data["channels"] = channel_data


async def save_pin_data_to_snapshot(guild: discord.Guild, snapshot_data: dict):
    pin_data = list()
    for channel in guild.text_channels:
        for message in await channel.pins():
            if message.author.bot:
                continue

            file_paths = []
            for attachment in message.attachments:
                print("STATE SAVER: Saving attachment: " + attachment.filename)
                file_path = f"data/snapshot_data/{guild.id}/{message.id}_{attachment.filename}"
                if os.path.exists(file_path):
                    print("STATE SAVER: Attachment already exists.")
                    file_paths.append(file_path)
                    continue
                await asyncio.sleep(5)
                print("STATE SAVER: File not found. Saving attachment to: " + file_path)
                await attachment.save(file_path)
                file_paths.append(file_path)

            pin_data.append(
                {
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "author_name": str(message.author),
                    "message_content": message.content,
                    "date": str(message.created_at)[:10],
                    "attachments": file_paths,
                }
            )
    snapshot_data["pins"] = pin_data


async def save_threads_to_snapshot(guild: discord.Guild, snapshot_data: dict):
    thread_data = list()
    for thread in guild.threads:
        thread_data.append(
            {
                "name": thread.name,
                "auto_archive_duration": thread.auto_archive_duration,
                "parent_channel_id": thread.parent.id,
                "parent_channel_name": thread.parent.name,
                "archived": thread.archived,
            }
        )
    snapshot_data["threads"] = thread_data


class StateSaver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        self.snapshot_loop.start()

    async def cog_unload(self):
        self.snapshot_loop.cancel()

    @discord.app_commands.command(
        name="_save_snapshot", description="Save the current server state to a file which can be restored later."
    )
    @discord.app_commands.guild_only()
    @discord.app_commands.default_permissions(administrator=True)
    async def save_snapshot(self, interaction: discord.Interaction):
        await interaction.response.defer()

        await self.create_snapshot(interaction.guild)

        await interaction.edit_original_response(content="Saved snapshot!")

    async def create_snapshot(self, guild: discord.Guild):
        folder_path = f"data/snapshot_data/{guild.id}"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        snapshot_data = dict()
        normalized_guild_name = guild.name.replace(" ", "_")
        snapshot_data["name"] = normalized_guild_name + "_" + datetime.now().strftime(f"%Y_%m_%d")
        await save_user_role_data_to_snapshot(guild, snapshot_data)
        await save_channel_data_to_snapshot(guild, snapshot_data)
        await save_pin_data_to_snapshot(guild, snapshot_data)
        await save_threads_to_snapshot(guild, snapshot_data)
        print("STATE SAVER: Saving snapshot data to file: " + snapshot_data["name"] + ".yml")
        with open(f"data/snapshot_data/{guild.id}/{snapshot_data['name']}.yml", "w") as snapshot_file:
            yaml.dump(snapshot_data, snapshot_file)

    @tasks.loop(hours=24)
    async def snapshot_loop(self):
        await asyncio.sleep(6000)
        print(f"SNAPSHOT_CREATOR: Creating Snapshot.")
        await self.create_snapshot(self.guild)


async def setup(bot):
    await bot.add_cog(StateSaver(bot))
