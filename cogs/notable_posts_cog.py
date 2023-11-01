"""Send posts with a lot of reactions to seperate channel"""
import asyncio

import discord
from discord.ext import commands
from discord.ext import tasks

from . import data_management

embed_post_lock = asyncio.Lock()


async def edit_notable_post(embed_message: discord.Message, reaction_message: discord.Message):
    reaction_embed = embed_message.embeds[0]
    reaction_embed.remove_field(-1)

    reaction_string = [f"{reaction.count} {reaction.emoji}" for reaction in reaction_message.reactions]
    reaction_string = ", ".join(reaction_string)
    reaction_embed.add_field(name="Reactions:", value=reaction_string, inline=False)
    await asyncio.sleep(10)
    await embed_message.edit(embed=reaction_embed)


async def highest_reaction_count(reaction_message: discord.Message):
    highest_reaction_count = max([reaction.count for reaction in reaction_message.reactions])
    return highest_reaction_count


class NotablePosts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.needed_reaction_count = 10

    async def cog_load(self):
        self.notable_post_info = dict()
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        self.notable_posts_channel = discord.utils.get(
            self.guild.channels, id=self.bot.config["notable_posts_channel_id"]
        )

        self.update_notable_posts.start()

    async def cog_unload(self):
        self.update_notable_posts.cancel()

    async def entry_exists(self, reaction_message):
        if reaction_message.id in self.notable_post_info:
            return True
        else:
            return False

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, member: discord.Member):
        if await self.entry_exists(reaction.message):
            return
        if not member.guild:
            return
        message_reaction_count = await highest_reaction_count(reaction.message)
        if message_reaction_count >= self.needed_reaction_count:
            await self.create_notable_post(self.notable_posts_channel, reaction.message, message_reaction_count)

    async def create_notable_post(
        self, notable_posts_channel: discord.TextChannel, reaction_message: discord.Message, reaction_count: int
    ):
        async with embed_post_lock:
            if await self.entry_exists(reaction_message):
                return
            print("NOTABLE POSTS: Creating notable post.")
            description = f"[Jump To Message]({reaction_message.jump_url})"
            if reaction_message.content:
                description += f"\n\n**Content:**\n{reaction_message.content}"

            reaction_embed = discord.Embed(description=description)
            reaction_embed.set_author(
                name=str(reaction_message.author), icon_url=str(reaction_message.author.avatar.url)
            )
            if reaction_message.attachments:
                reaction_embed.add_field(name="Media:", value="The post contained the following image:", inline=False)
                reaction_embed.set_image(url=reaction_message.attachments[0].url)
            reaction_string = [f"{reaction.count} {reaction.emoji}" for reaction in reaction_message.reactions]
            reaction_string = ", ".join(reaction_string)
            reaction_embed.add_field(name="Reactions:", value=reaction_string, inline=False)
            embed_message = await notable_posts_channel.send(embed=reaction_embed)
            self.notable_post_info[reaction_message.id] = (embed_message, reaction_message, reaction_count)

    @tasks.loop(minutes=5)
    async def update_notable_posts(self):
        await asyncio.sleep(60)
        print("NOTABLE POSTS: Checking for updates.")
        for embed_message, reaction_message, old_reaction_count in list(self.notable_post_info.values()):
            await asyncio.sleep(5)
            reaction_message = await reaction_message.channel.fetch_message(reaction_message.id)
            current_reaction_count = await highest_reaction_count(reaction_message)
            if current_reaction_count != old_reaction_count:
                await edit_notable_post(embed_message, reaction_message)


async def setup(bot):
    await bot.add_cog(NotablePosts(bot))
