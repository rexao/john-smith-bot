import discord
from discord import app_commands
from discord.ext import commands

from typing import List


class Emote(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.emotes = None

    async def cog_load(self) -> None:
        print(f"Extension loaded: {self.__class__.__name__}")
        return await super().cog_load()

    async def cog_unload(self) -> None:
        print(f"Extension unloaded: {self.__class__.__name__}")
        return await super().cog_unload()

    
    @app_commands.command(name='emote', description='Summon your favorite emotes.')
    @app_commands.describe(code='Look for an emote.')
    async def emote(self, interaction: discord.Interaction, code: str):
        if code not in self.emotes:
            return await interaction.response.send_message(content=f"Name a real emote buh", ephemeral=True)
        await interaction.response.send_message(self.emotes.get(code), ephemeral=True)
    
    @emote.autocomplete('code')
    async def emote_code_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        if self.emotes is None:
            self.emotes = {emote.name: f"{emote.url}?size=48&quality=lossless" for emote in self.bot.emojis if emote.guild.name.startswith('Labo ')}
        return [
            app_commands.Choice(name=emote, value=emote) for emote in self.emotes
            if current.lower() in emote.lower()
        ][:25]


async def setup(bot):
    await bot.add_cog(Emote(bot))
