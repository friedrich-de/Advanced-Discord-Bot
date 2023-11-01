import discord
from discord.ext import commands

import re
import aiofiles
import logging
import logging.handlers
import asyncio
from watchfiles import awatch

LOG_FILE = "data/logs/discord.log"


async def get_last_traceback():
    async with aiofiles.open(LOG_FILE) as log_file:
        log_content = await log_file.read()
        reversed_log_content = log_content[::-1]

    last_traceback_match = re.search(r".*?\d\d\d\d\[", reversed_log_content, re.DOTALL)
    first_index, second_index = last_traceback_match.regs[0]
    return reversed_log_content[first_index:second_index][::-1]


async def watch_file_changes(owner: discord.User):
    try:
        async for _ in awatch(LOG_FILE):
            last_traceback = await get_last_traceback()
            if not owner.dm_channel:
                await owner.create_dm()
            try:
                await owner.dm_channel.send(f"```python\n" f"{last_traceback}```")
            except discord.errors.HTTPException:
                error_embed = discord.Embed(
                    title="Long Traceback",
                    description=f"```python\n" f"{last_traceback}```",
                )
                await owner.dm_channel.send(embed=error_embed)
    except RuntimeError:
        pass


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        logger = logging.getLogger("discord")
        logger.setLevel(logging.ERROR)
        logging.getLogger("discord.http").setLevel(logging.INFO)

        handler = logging.handlers.RotatingFileHandler(
            filename=LOG_FILE,
            encoding="utf-8",
            maxBytes=2 * 512 * 512,  # 1 MiB
            backupCount=10,  # Rotate through 5 files
        )
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        stream_handler = logging.StreamHandler()
        logger.addHandler(stream_handler)

    async def cog_load(self):
        owner = await self.bot.fetch_user(self.bot.config["owner_id"])
        if not owner.dm_channel:
            await owner.create_dm()
        await owner.dm_channel.send(f"Bot started.")

        loop = asyncio.get_event_loop()
        loop.create_task(watch_file_changes(owner))


async def setup(bot):
    await bot.add_cog(Logging(bot))
