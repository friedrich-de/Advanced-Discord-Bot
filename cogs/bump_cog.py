import discord
from discord.ext import commands
from discord.ext import tasks

import asyncio
from datetime import datetime
from datetime import timedelta

from . import data_management
from . import utility_cog
from . import username_cog

#########################################

BUMP_DATA_FILE_NAME = "bump_data.yml"


async def process_dissoku(message: discord.Message):
    await asyncio.sleep(3)
    if not message.embeds:
        return False
    elif not message.embeds[0].fields:
        return False
    elif "をアップしたよ" in message.embeds[0].fields[0].name:
        return True
    else:
        return False


async def process_disboard(message: discord.Message):
    await asyncio.sleep(3)
    if not message.embeds:
        return False
    elif ":thumbsup:" in message.embeds[0].description:
        return True
    else:
        return False


BUMP_BOTS = {
    761562078095867916: ("Dissoku", "`/dissoku up`", 61.0, process_dissoku),
    302050872383242240: ("Disboard", "`/bump`", 121.0, process_disboard),
}

#########################################


async def save_time(bump_bot: discord.Member, bump_data):
    wait_time = timedelta(minutes=BUMP_BOTS[bump_bot.id][2])
    next_bump_time = datetime.utcnow() + wait_time
    bump_data[f"next_bump_time_{BUMP_BOTS[bump_bot.id][0]}"] = next_bump_time
    await data_management.save_data(bump_data, BUMP_DATA_FILE_NAME)


async def load_time(bump_bot: discord.Member, bump_data):
    next_bump_time = bump_data.get(f"next_bump_time_{BUMP_BOTS[bump_bot.id][0]}", datetime.utcnow())
    minutes_until_next_bump = (next_bump_time - datetime.utcnow()).total_seconds() / 60
    if minutes_until_next_bump > BUMP_BOTS[bump_bot.id][2] or minutes_until_next_bump < 1:
        minutes_until_next_bump = 1
    print(f"BUMP: {minutes_until_next_bump} minutes until next bump for {bump_bot.display_name}")
    return minutes_until_next_bump


#########################################


async def increment_leaderboard_points(bump_member: discord.Member, bump_data):
    bump_leaderboard = bump_data.get("leaderboard", {})
    old_points = bump_leaderboard.get(bump_member.id, 0)
    new_points = old_points + 1
    bump_leaderboard[bump_member.id] = new_points
    await data_management.save_data(bump_data, BUMP_DATA_FILE_NAME)
    return old_points, new_points


#########################################


async def make_leaderboard_post(bump_channel: discord.TextChannel, leaderboard_lines):
    past_pins = await utility_cog.get_past_user_pins(bump_channel, bump_channel.guild.me)
    leaderboard_fields = await utility_cog.create_fields(leaderboard_lines)
    leaderboard_embeds = await utility_cog.create_embeds_from_fields(leaderboard_fields, "Bump Leaderboard")
    await utility_cog.update_embeds(past_pins, leaderboard_embeds, "Bump Leaderboard", bump_channel)


class BumpReminder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tasks = []

    async def cog_load(self):
        await self.bot.wait_until_ready()
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        self.bump_channel = self.guild.get_channel(self.bot.config["bump"]["channel_id"])
        self.bump_role = self.guild.get_role(self.bot.config["bump"]["role_id"])
        self.bump_data = await data_management.load_data(BUMP_DATA_FILE_NAME)
        await self.launch_reminders()
        self.update_leaderboard.start()

    async def launch_reminders(self):
        for bump_bot_id in BUMP_BOTS:
            bump_bot = discord.utils.get(self.guild.members, id=bump_bot_id)
            if not bump_bot:
                continue

            loop = asyncio.get_running_loop()

            task = loop.create_task(self.bump_reminder(bump_bot))
            self.tasks.append(task)

    async def bump_reminder(self, bump_bot):
        def check_if_bot(message: discord.Message):
            if message.author == bump_bot and message.guild == bump_bot.guild and message.interaction:
                return True

        minutes_until_next_bump = await load_time(bump_bot, self.bump_data)
        while True:
            try:
                bot_message = await self.bot.wait_for(
                    "message", check=check_if_bot, timeout=minutes_until_next_bump * 60
                )

            except:
                bump_message = f"{self.bump_role.mention} Bump now with {BUMP_BOTS[bump_bot.id][1]}"
                await self.bump_channel.send(bump_message)

                minutes_until_next_bump = BUMP_BOTS[bump_bot.id][2]
                continue

            is_bump = await BUMP_BOTS[bump_bot.id][3](bot_message)

            if is_bump:
                await save_time(bump_bot, self.bump_data)
                minutes_until_next_bump = await load_time(bump_bot, self.bump_data)
                bump_member = bot_message.interaction.user
                bump_success_string = f"{bump_member.mention} Thanks for bumping!"

                old_points, new_points = await increment_leaderboard_points(bump_member, self.bump_data)
                bump_success_string = (
                    bump_success_string + f"\nIncreased your leaderboard points from "
                    f"**{old_points}** to **{new_points}**"
                )

                await self.bump_channel.send(bump_success_string, allowed_mentions=discord.AllowedMentions.none())

            else:
                minutes_until_next_bump = await load_time(bump_bot, self.bump_data)

    async def create_leaderboard_lines(self):
        bump_leaderboard = self.bump_data.get("leaderboard", {})
        sorted_leaderboard = sorted(bump_leaderboard.items(), key=lambda x: x[1], reverse=True)
        leaderboard_lines = []
        for i, (member_id, points) in enumerate(sorted_leaderboard):
            member = self.guild.get_member(member_id)
            if not member:
                member_name = await username_cog.get_user_name(self.bot, member_id)
                leaderboard_line = f"{i + 1}. {member_name} - {points}点"
                leaderboard_lines.append(leaderboard_line)
                continue
            leaderboard_line = f"{i + 1}. {member.mention} **{str(member)}** - {points}点"
            leaderboard_lines.append(leaderboard_line)
        return leaderboard_lines

    @tasks.loop(minutes=60.0)
    async def update_leaderboard(self):
        await utility_cog.random_delay()
        leaderboard_lines = await self.create_leaderboard_lines()
        await make_leaderboard_post(self.bump_channel, leaderboard_lines)


async def setup(bot):
    await bot.add_cog(BumpReminder(bot))
