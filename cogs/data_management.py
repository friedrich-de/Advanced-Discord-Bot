import yaml
import asyncio

data_lock = asyncio.Lock()


async def load_data(file_name, return_list=False):
    def load():
        try:
            with open(f"data/{file_name}") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            return [] if return_list else {}

    async with data_lock:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, load)


async def save_data(data, file_name):
    def save():
        with open(f"data/{file_name}", "w") as file:
            yaml.dump(data, file)

    async with data_lock:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, save)
