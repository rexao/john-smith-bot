import discord
from discord import app_commands, ui
from discord.ext import commands

import datetime
from typing import Dict, Optional


def calculate_time_elasped(dt: datetime.datetime, now: datetime.datetime = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(seconds=32400), 'Tokyo Standard Time'))):
    time_diff = now - dt
    if time_diff < datetime.timedelta(seconds=60):
        return f"{int(time_diff.total_seconds())} seconds ago"
    elif time_diff < datetime.timedelta(minutes=60):
        return f"{int(time_diff.total_seconds() // 60)} minutes ago"
    elif time_diff < datetime.timedelta(hours=24):
        return f"{int(time_diff.total_seconds() // 3600)} hours ago"
    elif time_diff < datetime.timedelta(days=30):
        return f"{int(time_diff.days)} days ago"
    elif time_diff < datetime.timedelta(days=365):
        return f"{int(time_diff.days // 30)} months ago"
    else:
        return f"{int(time_diff.days // 365)} years ago"


class Inspect(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        print(f"Extension loaded: {self.__class__.__name__}")
        return await super().cog_load()

    async def cog_unload(self) -> None:
        print(f"Extension unloaded: {self.__class__.__name__}")
        return await super().cog_unload()

    inspect = app_commands.Group(
        name='inspect', description='Access top secret information. More to come... :HACKERMANS:')

    @inspect.command(name='server', description='Get server info.')
    async def server(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("Hey bro this is not a server.")
        embeds = self._guild_generate_embeds(interaction.guild)
        view = self.Guild_View(embeds=embeds)
        await interaction.response.send_message(
            embed=embeds.get('main'),
            view=view
        )
        view.message = await (await interaction.original_response()).fetch()

    def _guild_generate_embeds(self, guild: discord.Guild) -> Dict[str, discord.Embed]:
        now = datetime.datetime.now(tz=datetime.timezone(
            datetime.timedelta(seconds=32400), 'Tokyo Standard Time'))

        main = discord.Embed(color=5793266, timestamp=now)
        main.set_author(name=guild.name, icon_url=guild.icon)
        main.add_field(
            name='Overview',
            value=f"""ID: `{guild.id}`
Owner: {guild.owner.mention}
Created: `{guild.created_at.strftime('%m/%d/%Y')} ({calculate_time_elasped(guild.created_at, now)})`
Boosts: `{guild.premium_subscription_count}`
Boost Tier: `{guild.premium_tier}`"""
        )
        main.add_field(
            name='Details',
            value=f"""Members: `{guild.member_count}`
Roles: `{len(guild.roles)}`
Categories: `{len(guild.categories)}`
Text Channels: `{len(guild.text_channels)}`
Voice Channels: `{len(guild.voice_channels)}`"""
        )
        main.add_field(
            name="Role List",
            value=" ".join(
                [role.mention for role in guild.roles if role.name != "@everyone"]),
            inline=False
        )
        main.set_thumbnail(url=guild.icon)

        icon = discord.Embed(color=5793266, title="Server Icon", timestamp=now)
        icon.set_author(name=guild.name, icon_url=guild.icon)
        icon.set_image(url=guild.icon)
        if guild.icon:
            icon.add_field(name="icon hash", value=f"`{guild.icon.key}`")
        else:
            icon.description = "There's no server icon."

        banner_background = discord.Embed(
            color=5793266, title="Server Banner Background", timestamp=now)
        banner_background.set_author(name=guild.name, icon_url=guild.icon)
        banner_background.set_image(url=guild.banner)
        if guild.banner:
            banner_background.add_field(
                name="banner hash", value=f"`{guild.banner.key}`")
        else:
            banner_background.description = "There's no server banner background."

        invite_background = discord.Embed(
            color=5793266, title="Server Invite Background", timestamp=now)
        invite_background.set_author(name=guild.name, icon_url=guild.icon)
        invite_background.set_image(url=guild.splash)
        if guild.splash:
            invite_background.add_field(
                name="splash hash", value=f"`{guild.splash.key}`")
        else:
            invite_background.description = "There's no server invite background."

        return {
            "main": main,
            "icon": icon,
            "banner_background": banner_background,
            "invite_background": invite_background
        }

    class Guild_View(ui.View):
        def __init__(self, *, embeds: Dict[str, discord.Embed], timeout: Optional[float] = None):
            self.embeds = embeds
            self.message = None
            super().__init__(timeout=timeout)
            self.remove_item(self.home)

        async def on_timeout(self):
            for child in self.children:
                child.disabled = True
            await self.message.edit(view=self)

        @ui.button(label='< Back')
        async def home(self, interaction: discord.Interaction, button: ui.Button):
            for item in self.children:
                self.remove_item(item)
            self.add_item(self.icon)
            self.add_item(self.banner_background)
            self.add_item(self.invite_background)
            await self.message.edit(embed=self.embeds.get('main'), view=self)
            await interaction.response.defer()

        @ui.button(label='Icon', style=discord.ButtonStyle.primary)
        async def icon(self, interaction: discord.Interaction, button: ui.Button):
            for item in self.children:
                self.remove_item(item)
            self.add_item(self.home)
            await self.message.edit(embed=self.embeds.get('icon'), view=self)
            await interaction.response.defer()

        @ui.button(label='Banner Background', style=discord.ButtonStyle.primary)
        async def banner_background(self, interaction: discord.Interaction, button: ui.Button):
            for item in self.children:
                self.remove_item(item)
            self.add_item(self.home)
            await self.message.edit(embed=self.embeds.get('banner_background'), view=self)
            await interaction.response.defer()

        @ui.button(label='Invite Background', style=discord.ButtonStyle.primary)
        async def invite_background(self, interaction: discord.Interaction, button: ui.Button):
            for item in self.children:
                self.remove_item(item)
            self.add_item(self.home)
            await self.message.edit(embed=self.embeds.get('invite_background'), view=self)
            await interaction.response.defer()
        
    @inspect.command(name='user', description='Get user info.')
    @app_commands.describe(user='Specify a user.')
    async def user(self, interaction: discord.Interaction, user: discord.Member = None):
        embeds = await self._user_generate_embeds(user or interaction.user)
        view = self.User_View(embeds=embeds)
        if not interaction.guild:
            view.remove_item(view.server_avatar)
        await interaction.response.send_message(
            embed=embeds.get('main'),
            view=view
        )
        view.message = await (await interaction.original_response()).fetch()
    
    async def _user_generate_embeds(self, user: discord.Member) -> Dict[str, discord.Embed]:
        now = datetime.datetime.now(tz=datetime.timezone(
            datetime.timedelta(seconds=32400), 'Tokyo Standard Time'))

        main = discord.Embed(color=5793266, timestamp=now)
        main.set_author(
            name=f"{user.nick} ({user.name}#{user.discriminator})" if getattr(user, 'nick', None) else f"{user.name}#{user.discriminator}",
            icon_url=user.display_avatar
        )
        avatar = main.copy()
        profile_banner = main.copy()
        server_avatar = main.copy()

        main.description = user.activity.name if getattr(user, 'activity', None) else None
        main.add_field(name='ID', value=f"`{user.id}`")
        if getattr(user, 'roles', None) and getattr(user, 'joined_at', None):
            main.add_field(name='Roles', value=' '.join([role.mention for role in user.roles if role.name!="@everyone"]))
            main.add_field(name='Joined Server', value=f"`{user.joined_at.strftime('%m/%d/%Y')} ({calculate_time_elasped(user.joined_at, now)})`")
        main.add_field(name='Joined Discord', value=f"`{user.created_at.strftime('%m/%d/%Y')} ({calculate_time_elasped(user.created_at, now)})`")
        main.set_thumbnail(url=user.display_avatar)

        avatar.title = "Avatar"
        if user.avatar:
            avatar.add_field(name="avatar hash", value=f"`{user.avatar.key}`")
            avatar.set_image(url=user.avatar)
        else:
            avatar.description = f"{user.mention} has no avatar."
            avatar.set_image(url=user.display_avatar)

        profile_banner.title = "Profile Banner"
        client_user = await self.bot.fetch_user(user.id)
        if client_user.banner:
            profile_banner.add_field(name="banner hash", value=f"`{client_user.banner.key}`")
            profile_banner.set_image(url=client_user.banner)
        else:
            profile_banner.description = f"{user.mention} has no profile banner."
        
        server_avatar.title = "Server Avatar"
        if getattr(user, 'guild_avatar', None):
            server_avatar.add_field(name="guild avatar hash", value=f"`{user.guild_avatar.key}`")
            server_avatar.set_image(url=user.guild_avatar)
        else:
            server_avatar.description = f"{user.mention} has no server avatar."
            server_avatar.set_image(url=user.display_avatar)
        
        return {
            "main": main, 
            "avatar": avatar,
            "profile_banner": profile_banner,
            "server_avatar": server_avatar
        }

    class User_View(ui.View):
        def __init__(self, *, embeds: Dict[str, discord.Embed], timeout: Optional[float] = None):
            self.embeds = embeds
            self.message = None
            super().__init__(timeout=timeout)
            self.remove_item(self.home)

        async def on_timeout(self):
            for child in self.children:
                child.disabled = True
            await self.message.edit(view=self)

        @ui.button(label='< Back')
        async def home(self, interaction: discord.Interaction, button: ui.Button):
            for item in self.children:
                self.remove_item(item)
            self.add_item(self.avatar)
            self.add_item(self.profile_banner)
            if interaction.guild:
                self.add_item(self.server_avatar)
            await self.message.edit(embed=self.embeds.get('main'), view=self)
            await interaction.response.defer()

        @ui.button(label='Avatar', style=discord.ButtonStyle.primary)
        async def avatar(self, interaction: discord.Interaction, button: ui.Button):
            for item in self.children:
                self.remove_item(item)
            self.add_item(self.home)
            await self.message.edit(embed=self.embeds.get('avatar'), view=self)
            await interaction.response.defer()

        @ui.button(label='Profile Banner', style=discord.ButtonStyle.primary)
        async def profile_banner(self, interaction: discord.Interaction, button: ui.Button):
            for item in self.children:
                self.remove_item(item)
            self.add_item(self.home)
            await self.message.edit(embed=self.embeds.get('profile_banner'), view=self)
            await interaction.response.defer()

        @ui.button(label='Server Avatar', style=discord.ButtonStyle.primary)
        async def server_avatar(self, interaction: discord.Interaction, button: ui.Button):
            for item in self.children:
                self.remove_item(item)
            self.add_item(self.home)
            await self.message.edit(embed=self.embeds.get('server_avatar'), view=self)
            await interaction.response.defer()


async def setup(bot):
    await bot.add_cog(Inspect(bot))
