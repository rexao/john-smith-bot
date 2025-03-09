import asyncio
import json
import logging
import os
from logging import handlers
from typing import List, Optional

import asyncpg
import discord
from aiohttp import ClientSession
from discord.ext import commands


class John_Smith(commands.Bot):
    def __init__(
        self,
        *args,
        initial_extensions: List[str],
        db_pool: asyncpg.Pool = None,
        web_client: ClientSession = None,
        playgroud_guild_id: Optional[int] = None,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.db_pool = db_pool,
        self.web_client = web_client
        self.playgroud_guild_id = playgroud_guild_id
        self.initial_extensions = initial_extensions

    async def setup_hook(self) -> None:
        self.bot_app_info = await self.application_info()
        self.owner_id = self.bot_app_info.owner.id

        for extension in self.initial_extensions:
            await self.load_extension(extension)

        if self.playgroud_guild_id:
            guild = discord.Object(id=self.playgroud_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)


async def main():
    logger = logging.getLogger('discord')
    # logger.setLevel(logging.INFO)

    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(
        '[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

    handler = handlers.RotatingFileHandler(
        filename='discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,
        backupCount=5
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # discord.utils.setup_logging(level=logging.INFO, root=False)

    with open('config.json', 'r') as f:
        config = json.load(f)
    
    async with ClientSession() as client: # , asyncpg.create_pool(user='postgres', command_timeout=30) as pool:
        cogs_defaults_dir = 'cogs/'  # defaults/
        cogs_defaults = [
            f"{cogs_defaults_dir+os.path.splitext(f)[0]}".replace('/', '.') for f in os.listdir(cogs_defaults_dir)
            if os.path.isfile(os.path.join(cogs_defaults_dir, f))
        ]
        async with John_Smith(
            ('$'),
            intents=discord.Intents.all(),
            # db_pool=pool,
            web_client=client,
            playgroud_guild_id=config.get(
                'discord', {}).get('playgroud_guild_id'),
            initial_extensions=cogs_defaults
        ) as bot:
            await bot.start(token=config.get('discord', {}).get('bot_token'))

asyncio.run(main())
