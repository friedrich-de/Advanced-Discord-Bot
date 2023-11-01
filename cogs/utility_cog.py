import discord
from discord.ext import commands
from discord.ext import tasks

import random
import asyncio


async def random_delay():
    delay = random.randint(600, 6000)
    await asyncio.sleep(delay)


async def get_past_user_pins(channel: discord.TextChannel, member: discord.Member):
    past_pins = [pin for pin in await channel.pins() if pin.author.id == member.id]
    return past_pins


async def create_fields(lines):
    fields = []
    current_field = []
    for line in lines:
        if len("\n".join(current_field)) + len(line) > 950:
            fields.append("\n".join(current_field))
            current_field = []
        current_field.append(line)
    fields.append("\n".join(current_field))
    return fields


async def create_embeds_from_fields(fields, embed_title, inline=False):
    embeds = []
    current_embed = discord.Embed(title=embed_title)
    for field in fields:
        if len(current_embed) + len(field) > 6000:
            embeds.append(current_embed)
            current_embed = discord.Embed(title=embed_title)
        current_embed.add_field(name="---", value=field, inline=inline)
    embeds.append(current_embed)
    return embeds


async def update_embeds(pins, embeds, embed_title, channel):
    filtered_pins = [pin for pin in pins if pin.embeds and pin.embeds[0].title == embed_title]
    if len(filtered_pins) < len(embeds):
        for i in range(len(filtered_pins), len(embeds)):
            new_pin = await channel.send(embed=embeds[i], allowed_mentions=discord.AllowedMentions.none())
            await new_pin.pin()
            filtered_pins.append(new_pin)

    for pin, embed in zip(filtered_pins, embeds):
        await pin.edit(embed=embed)


async def get_member_rank(member: discord.Member, bot):
    ranks = bot.config["rank_hierarchy"]
    for role in member.roles:
        if role.id in ranks:
            return role


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await self.bot.wait_until_ready()
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        self.thread_joiner.start()

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: discord.ext.commands.Context):
        """Sync commands to current guild."""
        self.bot.tree.copy_global_to(guild=discord.Object(id=ctx.guild.id))
        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
        await ctx.send(f"Synced commands to guild with id {ctx.guild.id}.")

    @commands.command()
    @commands.is_owner()
    async def clear_global_commands(self, ctx):
        """Clear all global commands."""
        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync()
        await ctx.send("Cleared global commands.")

    @commands.command()
    @commands.is_owner()
    async def clear_guild_commands(self, ctx):
        self.bot.tree.clear_commands(guild=discord.Object(id=ctx.guild.id))
        await self.bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
        await ctx.send(f"Cleared guild commands for guild with id {ctx.guild.id}.")

    @tasks.loop(hours=24)
    async def thread_joiner(self):
        await random_delay()
        for thread in self.guild.threads:
            if thread.me:
                continue
            else:
                await asyncio.sleep(5)
                print(f"UTILITY: Joining thread {thread.name}")
                await thread.join()


async def setup(bot):
    await bot.add_cog(Utility(bot))
