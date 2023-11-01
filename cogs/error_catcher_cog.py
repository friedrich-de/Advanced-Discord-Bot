"""Handle errors."""
from discord.ext import commands


class ErrorCatcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        pass

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandNotFound):
            return
        else:
            raise error


async def setup(bot):
    await bot.add_cog(ErrorCatcher(bot))
