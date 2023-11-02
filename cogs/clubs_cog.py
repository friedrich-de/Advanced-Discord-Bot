"""Framework for clubs with a role point system and scoreboard"""
import asyncio
import os

import discord
from discord.ext import commands
from discord.ext import tasks

from . import data_management
from . import username_cog
from . import utility_cog

#########################################


# Autocomplete functions


def generate_possible_time_periods():
    years = ["2019", "2020", "2021", "2022", "2023", "2024"]
    months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    possible_periods = []
    for year in years:
        for month in months:
            possible_periods.append(f"{year}-{month}")
    return possible_periods


POSSIBLE_PERIODS = generate_possible_time_periods()


async def time_period_autocomplete(interaction: discord.Interaction, current_input: str):
    possible_period_choices = [
        discord.app_commands.Choice(name=possible_period, value=possible_period)
        for possible_period in POSSIBLE_PERIODS
        if current_input in possible_period
    ]

    return possible_period_choices[0:25]


WORKS_DATA = dict()


async def generate_works_data():
    data_folder = "data"
    works_file_ending = "_read_works.yml"
    for file in os.listdir(data_folder):
        if file.endswith(works_file_ending):
            club_prefix = file.replace(works_file_ending, "")
            WORKS_DATA[club_prefix] = await data_management.load_data(f"{club_prefix}_read_works.yml")


async def works_autocomplete(interaction: discord.Interaction, current_input: str):
    challenge_prefix = interaction.namespace.club
    if not WORKS_DATA:
        await generate_works_data()
    work_data = WORKS_DATA[challenge_prefix]

    possible_choices = []
    for short_id in work_data:
        full_name = work_data[short_id][0]
        relevant_period = work_data[short_id][1] + "-" + work_data[short_id][2]

        if current_input.lower() in short_id.lower() or current_input.lower() in full_name.lower():
            possible_choices.append(
                discord.app_commands.Choice(name=f"{short_id} ({relevant_period})", value=short_id)
            )
            possible_choices.append(
                discord.app_commands.Choice(name=f"{full_name} ({relevant_period})", value=short_id)
            )

    return possible_choices[0:25]


USER_DATA = dict()


async def generate_user_data():
    data_folder = "data"
    user_file_ending = "_user_record.yml"
    for file in os.listdir(data_folder):
        if file.endswith(user_file_ending):
            club_prefix = file.replace(user_file_ending, "")
            USER_DATA[club_prefix] = await data_management.load_data(f"{club_prefix}_user_record.yml")


async def user_works_autocomplete(interaction: discord.Interaction, current_input: str):
    challenge_prefix = interaction.namespace.club
    member = interaction.namespace.member
    if not USER_DATA:
        await generate_user_data()
    all_user_data = USER_DATA[challenge_prefix]
    if not WORKS_DATA:
        await generate_works_data()
    work_data = WORKS_DATA[challenge_prefix]
    reward_user_data = all_user_data.get(member.id, list())
    possible_choices = []
    for work_id, points in reward_user_data:
        work_name, beginning_period, end_period, additional_info = work_data[work_id]
        if current_input.lower() in work_name.lower() or current_input.lower() in work_id.lower():
            possible_choices.append(discord.app_commands.Choice(name=f"{work_name} ({points} Points)", value=work_id))

    return possible_choices[0:25]


async def clubs_autocomplete(interaction: discord.Interaction, current_input: str):
    club_data = clubs_settings
    possible_choices = []
    for club in club_data:
        club_name = club["club_name"]
        club_abbreviation = club["club_prefix"]
        if current_input.lower() in club_abbreviation.lower() or current_input.lower() in club_name.lower():
            possible_choices.append(discord.app_commands.Choice(name=club_name, value=club_abbreviation))

    return possible_choices[0:25]


#########################################
async def update_leaderboard_pins(guild: discord.Guild, club_prefix, bot):
    club_data = [club for club in clubs_settings if club["club_prefix"] == club_prefix][0]
    club_channel = discord.utils.get(guild.channels, id=club_data["club_channel"])
    club_name = club_data["club_name"]
    all_user_data = await data_management.load_data(f"{club_prefix}_user_record.yml")

    leaderboard_lines = []
    sorted_ids = sorted(all_user_data, key=lambda key: sum(entry[1] for entry in all_user_data[key]), reverse=True)

    for index, user_id in enumerate(sorted_ids):
        member = guild.get_member(user_id)
        member_points = sum(entry[1] for entry in all_user_data[user_id])
        if not member:
            user_name = await username_cog.get_user_name(bot, user_id)
            if "Deleted User" in user_name:
                continue
            leaderboard_lines.append(f"{index + 1}. {user_name} {member_points}点")
        else:
            leaderboard_lines.append(f"{index + 1}. {member.mention} {member_points}点")

    user_pins = await utility_cog.get_past_user_pins(club_channel, guild.me)
    fields = await utility_cog.create_fields(leaderboard_lines)
    embeds = await utility_cog.create_embeds_from_fields(fields, f"{club_name} Leaderboard")
    print(f"CLUBS: Updating {club_name} leaderboard pins.")
    await utility_cog.update_embeds(user_pins, embeds, f"{club_name} Leaderboard", club_channel)


async def update_past_works_pins(guild: discord.Guild, club_prefix, bot):
    club_data = [club for club in clubs_settings if club["club_prefix"] == club_prefix][0]
    club_channel = discord.utils.get(guild.channels, id=club_data["club_channel"])
    club_name = club_data["club_name"]
    all_works_data = await data_management.load_data(f"{club_prefix}_read_works.yml")
    sorted_ids = sorted(all_works_data, key=lambda key: all_works_data[key][1])

    past_works_lines = []
    for index, work_id in enumerate(sorted_ids):
        work_name, start_date, end_date, extra_info = all_works_data[work_id]
        if start_date == end_date:
            past_works_lines.append(f"{index + 1}. **{start_date}** `{work_name}` {extra_info} | ID: `{work_id}`")
        else:
            past_works_lines.append(
                f"{index + 1}. **{start_date}-{end_date}** `{work_name}` {extra_info} | ID: `{work_id}`"
            )

    user_pins = await utility_cog.get_past_user_pins(club_channel, guild.me)
    fields = await utility_cog.create_fields(past_works_lines)
    embeds = await utility_cog.create_embeds_from_fields(fields, f"{club_name} Past Works")
    print(f"CLUBS: Updating {club_name} past works pins.")
    await utility_cog.update_embeds(user_pins, embeds, f"{club_name} Past Works", club_channel)


#########################################


async def give_out_reward_roles(bot: commands.Bot, guild: discord.Guild, club_prefix: str):
    clubs_data = clubs_settings
    club_data = [club for club in clubs_data if club["club_prefix"] == club_prefix][0]
    club_name = club_data["club_name"]
    reward_role_suffix = club_data["point_suffix"]
    user_data = await data_management.load_data(f"{club_prefix}_user_record.yml")

    for member_id in user_data:
        member = guild.get_member(member_id)
        if not member:
            continue
        total_points = sum([reward_data[1] for reward_data in user_data[member_id]])
        if total_points == 0:
            continue

        role_name = f"{total_points}{reward_role_suffix}"
        reward_role = discord.utils.get(guild.roles, name=role_name)
        if not reward_role:
            print(f"CLUBS: Creating nonexistent role {role_name}")
            reward_role = await guild.create_role(name=role_name, colour=discord.Colour.dark_grey())

        other_reward_roles = [
            role for role in guild.roles if role.name.endswith(reward_role_suffix) and role is not reward_role
        ]

        if reward_role in member.roles:
            continue
        else:
            await asyncio.sleep(5)
            await member.remove_roles(*other_reward_roles)
            print(f"CLUBS: Giving {member} the {reward_role.name} role for the {club_name}")
            await asyncio.sleep(5)
            await member.add_roles(reward_role)

    # Role cleanup
    roles_to_delete = [
        role for role in guild.roles if role.name.endswith(reward_role_suffix) and len(role.members) == 0
    ]
    for role in roles_to_delete:
        print(f"CLUBS: Deleting role {role.name} as it has no members.")
        await asyncio.sleep(5)
        await role.delete(reason="No members for role.")


async def give_out_checkpoint_roles(bot: commands.Bot, guild: discord.Guild, club_prefix):
    clubs_data = clubs_settings
    club_data = [club for club in clubs_data if club["club_prefix"] == club_prefix][0]
    checkpoint_role_data = club_data.get("check_point_roles")
    if not checkpoint_role_data:
        return

    all_checkpoint_roles = [discord.utils.get(guild.roles, id=role_id) for _, role_id in checkpoint_role_data.items()]
    user_data = await data_management.load_data(f"{club_prefix}_user_record.yml")

    for user_id in user_data:
        member = guild.get_member(int(user_id))
        if not member:
            continue
        total_points = sum([reward_data[1] for reward_data in user_data[user_id]])

        role_to_give = None
        for needed_points, role_id in checkpoint_role_data.items():
            if total_points >= needed_points:
                role_to_give = discord.utils.get(guild.roles, id=role_id)
                break
        if role_to_give:
            if role_to_give in member.roles:
                continue
            print(f"CLUBS: Giving {role_to_give.name} to {member}.")
            await asyncio.sleep(5)
            await member.remove_roles(*all_checkpoint_roles)
            await asyncio.sleep(5)
            await member.add_roles(role_to_give)


#########################################


class ReviewModal(discord.ui.Modal):
    def __init__(self, work_prefix, work_name, channel: discord.TextChannel, manager_role: discord.Role):
        super().__init__(title=f"Review for {work_name}"[0:45])
        self.work_prefix = work_prefix
        self.work_name = work_name
        self.channel = channel
        self.manager_role = manager_role

    review = discord.ui.TextInput(label="Review:", style=discord.TextStyle.paragraph, min_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        review_embed = discord.Embed(
            title=f"Review by {interaction.user.global_name} for {self.work_name}",
            description=self.review.value,
        )
        await self.channel.send(
            f"{self.manager_role.mention} | User {interaction.user.mention} has submitted"
            f" a review for **{self.work_name}**",
            embed=review_embed,
        )
        await interaction.response.send_message(f"Your review has been forwarded!", ephemeral=True)


#########################################


class Clubs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild = self.bot.get_guild(self.bot.config["guild_id"])
        self.clubs_settings = self.bot.config["clubs"]

        # For autocomplete
        global clubs_settings
        clubs_settings = self.bot.config["clubs"]

    async def cog_load(self):
        self.club_updates.start()

    async def check_if_club_manager(self, member, club_prefix):
        club_data = [club for club in self.clubs_settings if club["club_prefix"] == club_prefix][0]
        club_manager_role = discord.utils.get(self.guild.roles, id=club_data["manager_role"])
        if club_manager_role not in member.roles:
            return False
        return True

    @discord.app_commands.command(name="review", description="Write a review for a work you read/watched.")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(club="Name or shorthand of the club", work_name="The work you want to review")
    @discord.app_commands.autocomplete(club=clubs_autocomplete, work_name=works_autocomplete)
    @discord.app_commands.default_permissions(send_messages=True)
    async def review(self, interaction: discord.Interaction, club: str, work_name: str):
        club = [club_data for club_data in self.clubs_settings if club_data["club_prefix"] == club][0]
        work_data = await data_management.load_data(f"{club['club_prefix']}_read_works.yml")
        work_prefix = work_name
        try:
            work_name = work_data[work_prefix][0]
        except KeyError:
            await interaction.response.send_message(
                f"Work with ID `{work_prefix}` does not exist in the database. Did you select the option properly?",
                ephemeral=True,
            )
            return
        club_manager_role = discord.utils.get(interaction.guild.roles, id=club["manager_role"])
        club_channel = discord.utils.get(interaction.guild.channels, id=club["club_channel"])
        review_modal = ReviewModal(work_prefix, work_name, club_channel, club_manager_role)
        await interaction.response.send_modal(review_modal)

    @discord.app_commands.command(name="add_work", description="Add a work to a club.")
    @discord.app_commands.describe(
        club="Name or shorthand of the club",
        work_name=f"The full name of the work to add.",
        short_id=f"ID to uniquely identify the work.",
        beginning_period="What month the challenge should start.",
        end_period="What month the challenge should end.",
        additional_info="Additional info about the work, e.g. URL to VNDB or MAL.",
    )
    @discord.app_commands.autocomplete(
        club=clubs_autocomplete, beginning_period=time_period_autocomplete, end_period=time_period_autocomplete
    )
    async def add_work(
        self,
        interaction: discord.Interaction,
        club: str,
        work_name: str,
        short_id: str,
        beginning_period: str,
        end_period: str,
        additional_info: str,
    ):
        is_club_manager = await self.check_if_club_manager(interaction.user, club)
        if not is_club_manager:
            await interaction.response.send_message(
                f"You don't have permission to add works to this club.", ephemeral=True
            )
            return
        club = [club_data for club_data in self.clubs_settings if club_data["club_prefix"] == club][0]
        club_prefix = club["club_prefix"]
        work_data = await data_management.load_data(f"{club_prefix}_read_works.yml")
        if short_id in work_data:
            await interaction.response.send_message(
                f"Work with ID `{short_id}` already exists in the database.", ephemeral=True
            )
            return
        work_data[short_id] = [work_name, beginning_period, end_period, additional_info]
        await data_management.save_data(work_data, f"{club_prefix}_read_works.yml")
        await interaction.response.send_message(
            f"Added `{work_name}` for the time period "
            f"`{beginning_period}` to `{end_period}` with the unique ID "
            f"`{short_id}` to the `{club['club_name']}`."
        )
        await asyncio.sleep(5)
        await generate_works_data()

    @discord.app_commands.command(name="remove_work", description="Remove a work from a club.")
    @discord.app_commands.describe(club="Name or shorthand of the club", short_id="ID of the work to remove.")
    @discord.app_commands.autocomplete(club=clubs_autocomplete, short_id=works_autocomplete)
    async def remove_work(self, interaction: discord.Interaction, club: str, short_id: str):
        is_club_manager = await self.check_if_club_manager(interaction.user, club)
        if not is_club_manager:
            await interaction.response.send_message(
                f"You don't have permission to remove works from this club.", ephemeral=True
            )
            return
        work_data = await data_management.load_data(f"{club}_read_works.yml")
        if short_id not in work_data:
            await interaction.response.send_message(
                f"Work with ID `{short_id}` does not exist in the database.", ephemeral=True
            )
            return
        del work_data[short_id]
        await data_management.save_data(work_data, f"{club}_read_works.yml")
        await interaction.response.send_message(f"Removed work with ID `{short_id}` from the `{club}`.")
        await asyncio.sleep(5)
        await generate_works_data()

    @discord.app_commands.command(name="reward_work", description="Rewards a work to a user.")
    @discord.app_commands.describe(
        club="Name or shorthand of the club",
        work_name="ID of the work to reward.",
        member="The user to reward the work to.",
        points="How many points to reward.",
    )
    @discord.app_commands.autocomplete(club=clubs_autocomplete, work_name=works_autocomplete)
    async def reward_work(
        self, interaction: discord.Interaction, club: str, work_name: str, member: discord.Member, points: int
    ):
        is_club_manager = await self.check_if_club_manager(interaction.user, club)
        if not is_club_manager:
            await interaction.response.send_message(
                f"You don't have permission to reward works in this club.", ephemeral=True
            )
            return

        work_data = await data_management.load_data(f"{club}_read_works.yml")
        if work_name not in work_data:
            await interaction.response.send_message(
                f"Work with ID `{work_name}` does not exist in the database.", ephemeral=True
            )
            return
        full_work_name = work_data[work_name][0]
        user_data = await data_management.load_data(f"{club}_user_record.yml")
        if member.id not in user_data:
            user_data[member.id] = list()
            old_total_points = 0
        else:
            old_total_points = sum([reward_data[1] for reward_data in user_data[member.id]])

        for work_id, points in user_data[member.id]:
            if work_id == work_name:
                await interaction.response.send_message(
                    f"User `{member}` already has work `{work_name}` ({full_work_name}) rewarded to them in the `{club}`."
                )
                return

        user_data[member.id].append([work_name, points])
        new_total_points = old_total_points + points
        await data_management.save_data(user_data, f"{club}_user_record.yml")
        await interaction.response.send_message(
            f"Rewarded work with ID `{work_name}` ({full_work_name}) to user {member.mention} in the `{club}` bringing their total points from `{old_total_points}` to `{new_total_points}`."
        )
        await give_out_reward_roles(self.bot, self.guild, club)

    @discord.app_commands.command(name="unreward_work", description="Unrewards a work from a user.")
    @discord.app_commands.describe(
        club="Name or shorthand of the club", work_name="ID of the work to unreward.", member="The user to unreward."
    )
    @discord.app_commands.autocomplete(club=clubs_autocomplete, work_name=user_works_autocomplete)
    async def unreward_work(self, interaction: discord.Interaction, club: str, member: discord.Member, work_name: str):
        is_club_manager = await self.check_if_club_manager(interaction.user, club)
        if not is_club_manager:
            await interaction.response.send_message(
                f"You don't have permission to unreward works in this club.", ephemeral=True
            )
            return
        work_data = await data_management.load_data(f"{club}_read_works.yml")
        if work_name not in work_data:
            await interaction.response.send_message(
                f"Work with ID `{work_name}` does not exist in the database.", ephemeral=True
            )
            return
        full_work_name = work_data[work_name][0]
        user_data = await data_management.load_data(f"{club}_user_record.yml")
        if member.id not in user_data:
            await interaction.response.send_message(
                f"User `{member}` does not have any works rewarded to them in the `{club}`."
            )
            return

        current_user_data = user_data[member.id]
        old_total_points = sum([reward_data[1] for reward_data in current_user_data])
        for index, (work_id, points) in enumerate(current_user_data):
            if work_id == work_name:
                del current_user_data[index]
                user_data[member.id] = current_user_data
                break
        new_total_points = old_total_points - points
        await data_management.save_data(user_data, f"{club}_user_record.yml")
        await interaction.response.send_message(
            f"Unrewarded work with ID `{work_name}` ({full_work_name}) from user {member.mention} in the `{club}` bringing their total points from `{old_total_points}` to `{new_total_points}`."
        )

    @discord.app_commands.command(name="get_user_works", description="Get the list of works the user read/watched.")
    @discord.app_commands.describe(club="Name or shorthand of the club.", member="The user to get the works for.")
    @discord.app_commands.autocomplete(club=clubs_autocomplete)
    async def get_user_works(self, interaction: discord.Interaction, club: str, member: discord.Member):
        club_data = [club_data for club_data in self.clubs_settings if club_data["club_prefix"] == club][0]
        club_name = club_data["club_name"]
        user_data = await data_management.load_data(f"{club}_user_record.yml")
        if member.id not in user_data:
            await interaction.response.send_message(
                f"User `{member}` does not have any works rewarded to them in the `{club}`."
            )
            return
        work_data = await data_management.load_data(f"{club}_read_works.yml")

        work_strings = []
        for work_id, points in user_data[member.id]:
            work_name, beginning_period, end_period, additional_info = work_data[work_id]
            work_strings.append(f"`{work_id}`: {work_name} ({points} Points)")

        work_embed = discord.Embed(title=f"Works read by {member} in the {club_name}")
        work_embed.description = "\n".join(work_strings)

        await interaction.response.send_message(embed=work_embed)

    @discord.app_commands.command(name="get_work_users", description="Get the list of users that read/watched a work.")
    @discord.app_commands.describe(club="Name or shorthand of the club.", work_id="The name or the id of the work.")
    @discord.app_commands.autocomplete(club=clubs_autocomplete, work_id=works_autocomplete)
    async def get_work_users(self, interaction: discord.Interaction, club: str, work_id: str):
        work_data = await data_management.load_data(f"{club}_read_works.yml")
        all_user_data = await data_management.load_data(f"{club}_user_record.yml")

        if work_id not in work_data:
            await interaction.response.send_message(
                "Unknown work. Exiting...", ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
            )
            return

        work_name, beginning_period, end_period, additional_info = work_data[work_id]
        read_users_strings = []
        for user_id in all_user_data:
            member = interaction.guild.get_member(int(user_id))
            if not member:
                user_name = await username_cog.get_user_name(self.bot, int(user_id))
                if "Deleted User" in user_name:
                    continue
                if work_id in [read_data[0] for read_data in all_user_data[user_id]]:
                    read_users_strings.append(f"{user_name}")
                continue
            if work_id in [read_data[0] for read_data in all_user_data[user_id]]:
                read_users_strings.append(f"{member} {member.mention}")

        read_users_embed = discord.Embed(title=f"{len(read_users_strings)} users read/watched {work_name}.")
        read_users_embed.description = "\n".join(read_users_strings)

        await interaction.response.send_message(
            embed=read_users_embed, allowed_mentions=discord.AllowedMentions.none()
        )

    @tasks.loop(minutes=10)
    async def club_updates(self):
        await utility_cog.random_delay()
        for club in self.clubs_settings:
            club_prefix = club["club_prefix"]
            await update_leaderboard_pins(self.guild, club_prefix, self.bot)
            await update_past_works_pins(self.guild, club_prefix, self.bot)
            await give_out_reward_roles(self.bot, self.guild, club_prefix)
            await give_out_checkpoint_roles(self.bot, self.guild, club_prefix)


async def setup(bot):
    await bot.add_cog(Clubs(bot))
