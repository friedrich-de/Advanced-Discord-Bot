import asyncio
from datetime import datetime
from datetime import timedelta

import discord
from discord.ext import commands
from discord.ext import tasks

from . import data_management
from . import utility_cog

CUSTOM_ROLE_FILE_NAME = "deleted_messages.yml"

#########################################


async def retrieve_attachments(message: discord.Message):
    if message.attachments:
        files = list()
        for attachment in message.attachments:
            try:
                image_file = await attachment.to_file(use_cached=True)
                files.append(image_file)
            except discord.errors.HTTPException:
                return None
        return files
    else:
        return None


#########################################


class DeletedMessagesLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.deleter.start()
        self.delete_channel = self.bot.get_channel(self.bot.config["deleted_messages"]["log_channel"])
        self.clear_after_hours = self.bot.config["deleted_messages"]["clear_after_hours"]

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.id == self.bot.user.id:
            return
        if not self.delete_channel:
            return
        if self.delete_channel == message.channel:
            return

        current_time = datetime.utcnow()
        current_time_string = current_time.strftime("%b-%d %H:%M")

        content_embed = discord.Embed(
            title=f"Deleted message by {message.author} in #{message.channel.name} " f"at {current_time_string} UTC."
        )
        content_embed.set_thumbnail(url=message.author.display_avatar.url)
        if message.content:
            content_embed.add_field(name="Message content:", value=message.content[0:1000])

        information_string = (
            f"Name: {message.author}" f"\nMention: {message.author.mention}" f"\nID: {message.author.id}"
        )

        image_files = await retrieve_attachments(message)
        if image_files:
            information_string += f"\nContained **{len(image_files)}** attachments:"

        await self.delete_channel.send(
            content=information_string,
            files=image_files,
            embed=content_embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @tasks.loop(minutes=10.0)
    async def deleter(self):
        await utility_cog.random_delay()
        if not self.delete_channel:
            return
        delete_limit = timedelta(hours=self.clear_after_hours)
        await self.delete_channel.purge(before=datetime.utcnow() - delete_limit)


async def setup(bot):
    await bot.add_cog(DeletedMessagesLog(bot))
