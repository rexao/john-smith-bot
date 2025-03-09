import os
from typing import Literal, Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context, Greedy


class Core(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        print(f"Extension loaded: {self.__class__.__name__}")
        return await super().cog_load()
    
    async def cog_unload(self) -> None:
        print(f"Extension unloaded: {self.__class__.__name__}")
        return await super().cog_unload()

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: Context, guilds: Greedy[discord.Object], spec: Optional[Literal["guild", "copy", "clear"]] = None) -> None:
        if not guilds:
            if not ctx.guild or not spec:
                synced = await ctx.bot.tree.sync()
            elif spec == "guild":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "copy":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "clear":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            await ctx.reply(f"Synced {len(synced)} commands {'globally.' if not ctx.guild or not spec else 'to the current guild.'}")
            return
        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1
        await ctx.reply(f"Synced the tree to {ret}/{len(guilds)}.")

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: Context):
        reloading_message = await ctx.send(content='Reloading...')
        async with ctx.typing():
            for cog in list(self.bot.cogs):
                await self.bot.unload_extension(f'cogs.{cog}')
            for f in os.listdir('./cogs'):
                if f.endswith('.py'):
                    await self.bot.load_extension(f'cogs.{f[:-3]}')
            await reloading_message.reply(content='Reloaded!')


async def setup(bot):
    await bot.add_cog(Core(bot))
