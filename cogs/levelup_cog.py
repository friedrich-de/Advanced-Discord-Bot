import asyncio
import os
import re

import aiohttp
import discord
from discord.ext import commands

from . import data_management

KOTOBA_BOT_ID = 251239170058616833


async def give_reward_role(member, role_id_to_get, role_id_to_remove=None):
    """Gives and removes a role from the role name."""
    role_to_give = discord.utils.get(member.guild.roles, id=role_id_to_get)
    role_to_remove = None
    if role_id_to_remove:
        role_to_remove = discord.utils.get(member.guild.roles, id=role_id_to_remove)
    if role_to_give:
        await member.add_roles(role_to_give)
    if role_to_remove:
        await member.remove_roles(role_to_remove)


async def verify_quiz_settings(user_rank_data, quiz_data, member: discord.Member):
    """Ensures a user didn't use cheat settings for the quiz."""
    answer_count = user_rank_data["points"]
    answer_time_limit = user_rank_data["max_time"]
    font = user_rank_data["font"]
    font_size = user_rank_data["font_size"]
    fail_count = user_rank_data["allowed_fails"]
    command = user_rank_data["command"]

    try_again_line = f"\nUse the following command to try again: `{command}`"

    user_count = len(quiz_data["participants"])
    if user_count > 1:
        return False, "Quiz failed due to multiple people participating." + try_again_line

    shuffle = quiz_data["settings"]["shuffle"]
    if not shuffle:
        return False, "Quiz failed due to the shuffle setting being activated." + try_again_line

    is_loaded = quiz_data["isLoaded"]
    if is_loaded:
        return False, "Quiz failed due to being loaded." + try_again_line

    for deck in quiz_data["decks"]:
        if deck["mc"]:
            return False, "Quiz failed due to being set to multiple choice." + try_again_line

    for deck in quiz_data["decks"]:
        try:
            if deck["startIndex"]:
                return False, "Quiz failed due to having a start index." + try_again_line
        except KeyError:
            pass
        try:
            if deck["endIndex"]:
                return False, "Quiz failed due to having an end index." + try_again_line
        except KeyError:
            pass

    if answer_count != quiz_data["settings"]["scoreLimit"]:
        return False, "Set score limit and required score limit don't match." + try_again_line

    if answer_time_limit != quiz_data["settings"]["answerTimeLimitInMs"]:
        return False, "Set answer time does match required answer time." + try_again_line

    if font != "any" and font != quiz_data["settings"]["font"]:
        return False, "Set font does not match required font." + try_again_line

    if font_size != quiz_data["settings"]["fontSize"]:
        return False, "Set font size does not match required font size." + try_again_line

    failed_question_count = len(quiz_data["questions"]) - quiz_data["scores"][0]["score"]
    if failed_question_count > fail_count:
        return False, "Failed too many questions." + try_again_line

    if answer_count != quiz_data["scores"][0]["score"]:
        return False, "Not enough questions answered." + try_again_line

    combined_name = " + ".join([deck["name"] for deck in quiz_data["decks"]])

    return (
        True,
        f"{member.mention} has passed the {combined_name}!" f"\nUse `/levelup` to get the next level up command.",
    )


async def verify_if_rank_quiz(member: discord.Member, quiz_data, rank_data):
    """Determines if a quiz is a rank quiz. If so returns the rank data for the reward rank."""
    user_rank_data = False

    # Get corresponding data.
    for rank in rank_data:
        role_id_to_lose = rank["rank_to_have"]
        for role in member.roles:
            if role.id == role_id_to_lose:
                user_rank_data = rank

    if not user_rank_data:
        return False

    # Determine if current quiz is the correct one
    deck_strings = []
    for deck in quiz_data["decks"]:
        try:
            deck_strings.append(deck["shortName"])
        except KeyError:
            return  # Review quiz without deck name
    combined_deck_string = "+".join(deck_strings)

    quiz_name = user_rank_data["name"]

    if combined_deck_string == quiz_name:
        return user_rank_data
    else:
        return False


async def get_quiz_id(message: discord.Message):
    """Extract the ID of a quiz to use with the API."""
    try:
        if "Ended" in message.embeds[0].title:
            return re.findall(r"game_reports/([\da-z]*)", message.embeds[0].fields[-1].value)[0]
    except IndexError:
        return False
    except TypeError:
        return False


#########################################


class LevelUp(commands.Cog):
    def __init__(self, bot):
        self.aiosession = None
        self.bot = bot

    async def cog_load(self):
        self.aiosession = aiohttp.ClientSession()
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        rank_system_settings = self.bot.config["rank_system"]

        success_announce_channel_id = rank_system_settings["success_announce_channel"]
        self.success_announce_channel = discord.utils.get(self.guild.channels, id=success_announce_channel_id)

        failure_channel_ids = rank_system_settings["failure_announce_channels"]
        self.failure_channels = [
            discord.utils.get(self.guild.channels, id=channel_id) for channel_id in failure_channel_ids
        ]

        self.rank_data = rank_system_settings["rank_data"]

    async def cog_unload(self):
        await self.aiosession.close()

    @discord.app_commands.command(name="levelup", description="Get the next levelup command.")
    @discord.app_commands.guild_only()
    async def levelup(self, interaction: discord.Interaction):
        user_rank_data = None

        for rank_data in self.rank_data:
            role_id_to_have = rank_data["rank_to_have"]
            for role in interaction.user.roles:
                if role.id == role_id_to_have:
                    user_rank_data = rank_data

        if user_rank_data:
            command = user_rank_data["command"]
            await interaction.response.send_message(command, ephemeral=True)
        else:
            await interaction.response.send_message(
                "There is no level-up command for your current ranks.", ephemeral=True
            )

    @discord.app_commands.command(name="levelup_all", description="See all level up commands.")
    @discord.app_commands.guild_only()
    async def levelup_all(self, interaction: discord.Interaction):
        command_list = [rank_data["command"] for rank_data in self.rank_data]
        await interaction.response.send_message("\n".join(command_list), ephemeral=True)

    @discord.app_commands.command(name="rankusers", description="See all users with a specific role.")
    @discord.app_commands.describe(role="Role for which all members should be displayed.")
    @discord.app_commands.guild_only()
    async def rankusers(self, interaction: discord.Interaction, role: discord.Role):
        member_count = len(role.members)
        mention_string = []
        for member in role.members:
            mention_string.append(member.mention)
        if len(" ".join(mention_string)) < 500:
            mention_string.append(f"\nA total {member_count} members have the role {role.mention}.")
            await interaction.response.send_message(
                " ".join(mention_string), allowed_mentions=discord.AllowedMentions.none()
            )
        else:
            member_string = [str(member) for member in role.members]
            member_string.append(f"\nTotal {member_count} members.")
            with open("data/rank_user_count.txt", "w") as text_file:
                text_file.write("\n".join(member_string))
            await interaction.response.send_message("Here you go:", file=discord.File("data/rank_user_count.txt"))
            os.remove("data/rank_user_count.txt")

    @discord.app_commands.command(name="ranktable", description="Get an overview of the amount of users in each rank.")
    @discord.app_commands.guild_only()
    async def ranktable(self, interaction: discord.Interaction):
        rank_role_ids = self.bot.config["rank_hierarchy"]
        rank_roles = [discord.utils.get(interaction.guild.roles, id=role_id) for role_id in rank_role_ids]
        duplicate_role_members = []
        missing_role_members = []
        total_members = 0
        rank_count = dict()
        for member in interaction.guild.members:
            role_count = 0
            if member.bot:
                continue
            total_members += 1
            for role in member.roles:
                if role in rank_roles:
                    role_count += 1
                    rank_count[role.name] = rank_count.get(role.name, 0) + 1
            if role_count == 0:
                missing_role_members.append(member)
            elif role_count > 1:
                duplicate_role_members.append(member)

        ranktable_message = ["**Role Distribution**"]
        for role_name in [role.name for role in rank_roles]:
            ranktable_message.append(f"{role_name}: {rank_count[role_name]}")

        if duplicate_role_members:
            duplicate_mention_string = " ".join([member.mention for member in duplicate_role_members])
            ranktable_message.append(f"\nMembers with duplicate roles:\n {duplicate_mention_string}")

        if missing_role_members:
            missing_mention_string = " ".join([member.mention for member in missing_role_members])
            ranktable_message.append(f"\nMembers with missing roles:\n {missing_mention_string}")

        ranktable_message.append(f"\nTotal member count: {total_members}")
        ranktable_string = "\n".join(ranktable_message)

        await interaction.response.send_message(ranktable_string, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener(name="on_message")
    async def level_up_routine(self, message: discord.Message):
        if not message.author.id == KOTOBA_BOT_ID:
            return

        quiz_id = await get_quiz_id(message)
        if not quiz_id:
            return

        quiz_data = await self.extract_quiz_data_from_id(quiz_id)

        member = message.guild.get_member(int(quiz_data["participants"][0]["discordUser"]["id"]))
        user_rank_data = await verify_if_rank_quiz(member, quiz_data, self.rank_data)

        if user_rank_data:
            passed, info = await verify_quiz_settings(user_rank_data, quiz_data, member)
        else:
            passed = False
            info = "Wrong quiz for your current level."

        if passed:
            role_id_to_get = user_rank_data["rank_to_get"]
            role_id_to_remove = user_rank_data["rank_to_have"]
            await self.success_announce_channel.send(info, file=discord.File(user_rank_data["file_to_send"]))
            await give_reward_role(member, role_id_to_get, role_id_to_remove)
        else:
            if message.channel in self.failure_channels:
                await message.channel.send(f"{member.mention} {info}")

    async def extract_quiz_data_from_id(self, quiz_id):
        jsonurl = f"https://kotobaweb.com/api/game_reports/{quiz_id}"
        await asyncio.sleep(1)
        async with self.aiosession.get(jsonurl) as resp:
            return await resp.json()


async def setup(bot):
    await bot.add_cog(LevelUp(bot))
