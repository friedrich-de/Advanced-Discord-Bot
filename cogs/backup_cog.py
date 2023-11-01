import discord
from discord.ext import commands
from discord.ext import tasks

from . import data_management
from . import utility_cog

import os
import asyncio

from b2sdk.v2 import *

BACKUP_DIR = "data"


class BackupData(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bucket_settings = await data_management.load_data("b2_settings.yml")
        self.backup_routine.start()

    async def get_files_to_upload(self):
        files = []
        for dirpath, dirnames, filenames in os.walk(BACKUP_DIR):
            for filename in filenames:
                files.append(os.path.join(dirpath, filename))

        return files

    async def upload_file(self, file_path, bucket):
        def upload():
            bucket.upload_local_file(
                local_file=file_path,
                file_name=file_path,
            )
            print(f"BACKUP: Uploaded {file_path}")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, upload)

    @tasks.loop(hours=24)
    async def backup_routine(self):
        await utility_cog.random_delay()
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        application_key_id = self.bucket_settings["key-id"]
        application_key = self.bucket_settings["secret-key"]
        b2_api.authorize_account("production", application_key_id, application_key)

        files_to_upload = await self.get_files_to_upload()
        bucket = b2_api.get_bucket_by_name(self.bucket_settings["backup_bucket"])
        for file in files_to_upload:
            await self.upload_file(file, bucket)


async def setup(bot):
    await bot.add_cog(BackupData(bot))
