"""Cog providing some basic moderator tools"""
from datetime import datetime

import discord
from discord.ext import commands


class ModerationModal(discord.ui.Modal):
    def __init__(self, action_function_name, target_object, bot, moderator_channel):
        super().__init__(title="Moderator Report")

        self.action_function_name = action_function_name.lower().replace(" ", "_")
        self.target_object = target_object
        self.bot = bot
        self.moderator_channel = moderator_channel

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        report_embed = discord.Embed(
            title="Moderator Log",
            description=f"{interaction.user.mention} just performed a moderator action.",
            colour=discord.Colour.red(),
        )

        reason = self.children[0].value

        if self.action_function_name == "delete_message":
            performed_action = await self.delete_message()
            if not performed_action:
                await interaction.edit_original_response(
                    content=f"You cannot perform this action on that user, {interaction.user.display_name}!"
                )
                return
            else:
                report_embed.add_field(
                    name="Message Deletion",
                    value=f"**Message author**: {self.target_object.author.mention}"
                    f"\n**Name**: `{str(self.target_object.author)}`"
                    f"\n**Author ID**: `{self.target_object.author.id}`"
                    f"\n**Channel**: {self.target_object.channel.mention}"
                    f"\n**Reason**: `{reason}`",
                )
                await interaction.channel.send(embed=report_embed)
                report_embed.add_field(
                    name="**Message Content**", value=f"`{self.target_object.content[0:500]}`", inline=False
                )
                report_embed.add_field(
                    name="Attachments", value=f"Message had `{len(self.target_object.attachments)}` attachments."
                )

        elif self.action_function_name == "purge_messages":
            performed_action = await self.purge_messages()
            if not performed_action:
                await interaction.edit_original_response(
                    content=f"You cannot perform this action on that user, {interaction.user.display_name}!"
                )
                return
            else:
                messages_content = performed_action[1]
                report_embed.add_field(
                    name=f"Message Purge ({self.children[1].value} Messages)",
                    value=f"**Messages author**: {self.target_object.author.mention}"
                    f"\n**Name**: `{str(self.target_object.author)}`"
                    f"\n**Author ID**: `{self.target_object.author.id}`"
                    f"\n**Channel**: {self.target_object.channel.mention}"
                    f"\n**Reason**: `{reason}`",
                )
                await interaction.channel.send(embed=report_embed)
                report_embed.add_field(name="**Messages Content**", value=f"`{messages_content}`\n[...]", inline=False)

        elif self.action_function_name == "toggle_pin":
            try:
                pin_action = await self.toggle_pinned()
            except discord.errors.HTTPException:
                await interaction.edit_original_response(
                    content=f"Message seems to have been deleted., {interaction.user.display_name}!"
                )
                return
            if pin_action:
                report_embed.add_field(
                    name=f"Pin",
                    value=f"**Message**: [Jump To Message]({self.target_object.jump_url})" f"\n**Reason**: `{reason}`",
                )
            else:
                report_embed.add_field(
                    name=f"Unpin",
                    value=f"**Message** : [Jump To Message]({self.target_object.jump_url})"
                    f"\n**Reason**: `{reason}`",
                )

            await interaction.channel.send(embed=report_embed)

        await self.moderator_channel.send(embed=report_embed)
        await interaction.edit_original_response(
            content=f"Thank you for your hard work, {interaction.user.display_name}!"
        )

    async def delete_message(self):
        self.target_object: discord.Message
        try:
            if self.target_object.author.guild_permissions.administrator:
                return False
        except AttributeError:
            pass
        await self.target_object.delete()
        return True

    async def purge_messages(self):
        self.target_object: discord.Message
        try:
            message_count = int(self.children[1].value)
        except ValueError:
            message_count = 1
        member_to_purge = self.target_object.author

        self.target_object: discord.Message
        try:
            if member_to_purge.guild_permissions.administrator:
                return False
        except AttributeError:
            pass

        count = 1

        def purge_check(message):
            message_date = message.created_at.replace(tzinfo=None)
            time_difference = datetime.utcnow() - message_date
            if time_difference.days >= 14:
                return False
            if message.author == member_to_purge:
                nonlocal count
                count += 1
                return count <= message_count
            else:
                return False

        deleted_messages = await self.target_object.channel.purge(
            limit=200, check=purge_check, before=self.target_object, reason=self.children[0].value
        )

        messages_content_list = [message.content for message in deleted_messages]
        messages_content_list.insert(0, self.target_object.content)
        await self.target_object.delete()
        return True, "\n".join(messages_content_list)[0:1000]

    async def toggle_pinned(self):
        self.target_object: discord.Message
        if self.target_object.pinned:
            await self.target_object.unpin(reason=self.children[0].value)
            return False
        else:
            await self.target_object.pin(reason=self.children[0].value)
            return True


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.delete_ctx_menu = discord.app_commands.ContextMenu(name="Delete message", callback=self.delete_message)
        self.purge_ctx_menu = discord.app_commands.ContextMenu(name="Purge messages", callback=self.purge_messages)
        self.pin_ctx_menu = discord.app_commands.ContextMenu(name="Toggle pin", callback=self.toggle_pin)

    async def cog_load(self):
        moderator_channel_id = self.bot.config["mod_channel_id"]
        self.moderator_channel = self.bot.get_channel(moderator_channel_id)
        self.bot.tree.add_command(self.delete_ctx_menu)
        self.bot.tree.add_command(self.purge_ctx_menu)
        self.bot.tree.add_command(self.pin_ctx_menu)

    @discord.app_commands.default_permissions(administrator=True)
    async def delete_message(self, interaction: discord.Interaction, message: discord.Message):
        moderation_modal = ModerationModal(interaction.command.name, message, self.bot, self.moderator_channel)
        moderation_modal.add_item(discord.ui.TextInput(label="Reason for delete", min_length=4, max_length=400))
        await interaction.response.send_modal(moderation_modal)

    @discord.app_commands.default_permissions(administrator=True)
    async def purge_messages(self, interaction: discord.Interaction, message: discord.Message):
        moderation_modal = ModerationModal(interaction.command.name, message, self.bot, self.moderator_channel)
        moderation_modal.add_item(
            discord.ui.TextInput(
                label="Reason for purge",
                min_length=4,
                max_length=400,
                style=discord.TextStyle.paragraph,
                placeholder="Beware the bot can only see 200 msgs back from "
                "the msg you selected and no further than two "
                "weeks.",
            )
        )
        moderation_modal.add_item(
            discord.ui.TextInput(label="Message Count", min_length=1, max_length=2, default="20")
        )
        await interaction.response.send_modal(moderation_modal)

    @discord.app_commands.default_permissions(administrator=True)
    async def toggle_pin(self, interaction: discord.Interaction, message: discord.Message):
        moderation_modal = ModerationModal(interaction.command.name, message, self.bot, self.moderator_channel)
        moderation_modal.add_item(discord.ui.TextInput(label="Reason for toggling pin", min_length=4, max_length=400))
        await interaction.response.send_modal(moderation_modal)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
