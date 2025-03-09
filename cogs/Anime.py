import asyncio
import datetime
import json
import random
import re
import requests
import sqlite3
import tabulate
from typing import Any, Dict, List, Literal, Optional

import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
async def setup(bot):
    await bot.add_cog(Anime(bot))

from jikanpy import Jikan, AioJikan
def jikan_seasons_ducktape(year: Optional[int] = None, season: Optional[str] = None) -> List[Dict[str, Any]]:
    if not (year and season):
        response = requests.get(f'https://api.jikan.moe/v4/seasons/now')    
        json = response.json()
        year, season = json['data'][0]['year'], json['data'][0]['season']
    else:
        response = requests.get(f'https://api.jikan.moe/v4/seasons/{year}/{season}')
        json = response.json()
        results = [{'data': json['data']}]
    if json['pagination']['last_visible_page'] > 1:
        for i in range(1, json['pagination']['last_visible_page']):
            response = requests.get(f'https://api.jikan.moe/v4/seasons/{year}/{season}?page={i+1}')
            json = response.json()
            results.append(
                {'data': json['data']}
            )
    return results
jikan, aiojikan = Jikan(selected_base='https://api.jikan.moe/v4'), AioJikan(selected_base='https://api.jikan.moe/v4')
jikan.seasons = jikan_seasons_ducktape



class Database():
    def __init__(self, *, path: str = 'anime_v4.db') -> None:
        self.path = path
        super().__init__()

    def dict_factory(self, cursor: sqlite3.Cursor, row: sqlite3.Row) -> Dict[str, Any]:
        col_names = [col[0] for col in cursor.description]
        try:
            return {key: value for key, value in zip(col_names, row)}
        except TypeError:
            return None

    async def setup_guild(self, guild: discord.Guild):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        c = db.cursor()

        c.execute(f"""
            CREATE TABLE IF NOT EXISTS animelist_{guild.id} (
                mal_id INT, 
                titles VARCHAR,
                jikan_response VARCHAR,
                guild_data VARCHAR,
                added_by INT,
                added_on VARCHAR,
                last_edited_by INT,
                last_edited_on VARCHAR
            )
        """)
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INT,
                parent_channel INT,
                main INT,
                episodes INT,
                threads INT
            )
        """)
        db.commit()

        c.execute(f"""
            SELECT * FROM guild_config
            WHERE guild_id = ?
        """, (guild.id,))
        if not c.fetchall():
            c.execute(f"""
                INSERT INTO guild_config
                VALUES (?, ?, ?, ?, ?)
            """, (guild.id, None, None, None, None))
            db.commit()

        c.execute(f"""
            SELECT * FROM guild_config
            WHERE guild_id = ?
        """, (guild.id,))
        query = self.dict_factory(cursor=c, row=c.fetchone())
        for column in query:
            if column == 'guild_id':
                continue
            elif column == 'parent_channel':
                category = discord.utils.get(guild.categories, id=query[column])
                if not category:
                    category = await guild.create_category(name='/anime', position=1)
                    c.execute(f"""
                        UPDATE guild_config
                        SET parent_channel = ?
                        WHERE guild_id = ?
                    """, (category.id, guild.id,))
            else:
                channel = discord.utils.get(guild.text_channels, id=query[column])
                if not channel:
                    channel = await guild.create_text_channel(name=column, category=category)
                    c.execute(f"""
                        UPDATE guild_config
                        SET {column} = ?
                        WHERE guild_id = ?
                    """, (channel.id, guild.id,))
        db.commit()

        c.execute(f"""
            SELECT * FROM guild_config
            WHERE guild_id = ?
        """, (guild.id,))
        query = self.dict_factory(cursor=c, row=c.fetchone())
        idx = 0
        for column in query:
            if column in ['guild_id', 'parent_channel']:
                continue
            channel = discord.utils.get(guild.text_channels, id=query[column])
            await channel.edit(position=idx)
            idx += 1
        db.commit()
        db.close()
    
    def config_query(self, guild: discord.Guild) -> Dict[str, Any]:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute(f"""
            SELECT * FROM guild_config
            WHERE guild_id = ?
        """, (guild.id,))
        query = c.fetchone()
        return query
    
    def animelist_insert(
        self,
        guild: discord.Guild,
        added_by: discord.User,
        added_on: datetime.datetime,
        jikan_response: dict,
        guild_data: dict = None
    ) -> Literal['INSERT', 'UPDATE']:
        if self.animelist_query_by_id(guild=guild, mal_id=jikan_response['full']['data']['mal_id']):
            return self.animelist_update(
                guild=guild,
                mal_id=jikan_response['full']['data']['mal_id'],
                last_edited_by=added_by,
                last_edited_on=added_on,
                jikan_response=jikan_response,
                guild_data=guild_data
            )

        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute(f"""
            INSERT INTO animelist_{guild.id}
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            jikan_response['full']['data']['mal_id'],
            json.dumps(utils.get_anime_titles(jikan_response['full'])),
            json.dumps(jikan_response),
            json.dumps(guild_data),
            added_by.id,
            str(added_on),
            None,
            None
        ))
        db.commit()
        db.close()
        return 'INSERT'

    def animelist_update(
        self,
        guild: discord.Guild,
        mal_id: int,
        last_edited_by: discord.User,
        last_edited_on: datetime.datetime,
        jikan_response: dict = None,
        guild_data: dict = None
    ) -> Literal['update']:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        c = db.cursor()

        c.execute(f"""
            UPDATE animelist_{guild.id}
            SET last_edited_by = ?, last_edited_on = ?
            WHERE mal_id = ?
        """, (last_edited_by.id, str(last_edited_on), mal_id,))
        
        if isinstance(guild_data, dict):
            c.execute(f"""
                UPDATE animelist_{guild.id}
                SET guild_data = ?
                WHERE mal_id = ?
            """, (json.dumps(guild_data), mal_id,))

        if isinstance(jikan_response, dict):
            c.execute(f"""
                UPDATE animelist_{guild.id}
                SET mal_id = ?, titles = ?, jikan_response = ?
                WHERE mal_id = ?
            """, (
                mal_id, 
                json.dumps(utils.get_anime_titles(jikan_response['full'])), 
                json.dumps(jikan_response), 
                mal_id,
            ))
        
        db.commit()
        db.close()
        return 'UPDATE'

    def animelist_delete(self, guild: discord.Guild, mal_id: int):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute(f"""
            DELETE FROM animelist_{guild.id}
            WHERE mal_id = ?
        """, (mal_id,))
        db.commit()
        db.close()

    def animelist_query_by_id(self, guild: discord.Guild, mal_id: int) -> dict:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute(f"""
            SELECT * FROM animelist_{guild.id}
            WHERE mal_id = ?
        """, (mal_id,))
        result = {}
        query = self.dict_factory(cursor=c, row=c.fetchone())
        if not query:
            return None
        for cell in query:
            try:
                data = json.loads(query[cell])
            except (json.decoder.JSONDecodeError, TypeError):
                try:
                    data = datetime.datetime.fromisoformat(query[cell])
                except (ValueError, TypeError):
                    data = query[cell]
            result[cell] = data
        return result

    def animelist_fast_query_by_id(self, guild: discord.Guild, mal_id: int) -> dict:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute(f"""
            SELECT mal_id, titles
            FROM animelist_{guild.id}
            WHERE mal_id = ?
        """, (mal_id,))
        result = {}
        query = self.dict_factory(cursor=c, row=c.fetchone())
        if not query:
            return None
        for cell in query:
            try:
                data = json.loads(query[cell])
            except (json.decoder.JSONDecodeError, TypeError):
                data = query[cell]
            result[cell] = data
        return result
    
    def animelist_query_all(self, guild: discord.Guild) -> List[dict]:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute(f"""
            SELECT * FROM animelist_{guild.id}
        """)
        query = c.fetchall()
        results = []
        for entry in query:
            entry = self.dict_factory(cursor=c, row=entry)
            result = {}
            for cell in entry:
                try:
                    data = json.loads(entry[cell])
                except (json.decoder.JSONDecodeError, TypeError):
                    try:
                        data = datetime.datetime.fromisoformat(entry[cell])
                    except (ValueError, TypeError):
                        data = entry[cell]
                result[cell] = data
            results.append(result)
        return results

    def animelist_fast_query_all(self, guild: discord.Guild) -> List[dict]:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute(f"""
            SELECT mal_id, titles
            FROM animelist_{guild.id}
        """)
        query = c.fetchall()
        results = []
        for entry in query:
            entry = self.dict_factory(cursor=c, row=entry)
            result = {}
            for cell in entry:
                try:
                    data = json.loads(entry[cell])
                except (json.decoder.JSONDecodeError, TypeError):
                    data = entry[cell]
                result[cell] = data
            results.append(result)
        return results

class Utils():
    def __init__(self, *, selected_base: str = None) -> None:
        self.base = 'https://api.jikan.moe/v4' if not selected_base else selected_base
        self.weekdays = ['Sundays', 'Mondays', 'Tuesdays', 'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays']
        self.seasons_str_cached = self.get_seasons_str()
        pass

    def get_seasons_str(self) -> List[str]:
        response = requests.get(f'https://api.jikan.moe/v4/seasons/now')    
        json = response.json()
        current_year, current_season = json['data'][0]['year'], json['data'][0]['season']
        
        response = requests.get(f'{self.base}/seasons')
        json = response.json()
        results = []
        for year in json['data']:
            year['seasons'].reverse()
            for season in year['seasons']:
                if season==current_season and year['year']==current_year:
                    results.append(f"{season.capitalize()} {year['year']} (Current)")
                else:
                    results.append(f"{season.capitalize()} {year['year']}")
        return results
    
    
    def get_season_shows_paged(self, year: Optional[int] = None, season: Optional[str] = None) -> List[List[Dict[str, int | str]]]:
        results = []
        response = jikan.seasons(year=year, season=season)
        for page in response:
            entries_in_page = []
            for anime in page['data']:
                entries_in_page.append({
                    'mal_id': anime['mal_id'],
                    'title_english': anime['title_english'] if anime['title_english'] else anime['title'],
                    'title_japanese': anime['title_japanese'] if anime['title_japanese'] else anime['title']
                })
            results.append(entries_in_page)
        return results
    
    def get_anime_titles(self, anime: Dict[str, Any]) -> Dict[str, str]:
        return {
            'mal_id': anime['data']['mal_id'],
            'title_english': anime['data']['title_english'] if anime['data']['title_english'] else anime['data']['title'],
            'title_japanese': anime['data']['title_japanese'] if anime['data']['title_japanese'] else anime['data']['title']
        }
    
    def get_anime_image_jpg(self, anime: Dict[str, Any]) -> str:
        if 'large_image_url' in anime['data']['images']['jpg']:
            image_url = anime['data']['images']['jpg']['large_image_url']
        elif 'image_url' in anime['data']['images']['jpg']:
            image_url = anime['data']['images']['jpg']['image_url']
        elif 'small_image_url' in anime['data']['images']['jpg']:
            image_url = anime['data']['images']['jpg']['small_image_url']
        else:
            image_url = None
        return image_url
    
    def get_anime_premiered_str(self, anime: Dict[str, Any]) -> str:
        season, year = anime['data']['season'], anime['data']['year']
        premiered = f'{season.capitalize()} {year}' if (season and year) else 'Unknown'
        return premiered

    def get_anime_studios(self, anime: Dict[str, Any]) -> List[str]:
        return [studio['name'] for studio in anime['data']['studios']]

    def get_guild_average_score(self, scores: Dict[int, float]) -> str | None:
        scores = [scores[user] for user in scores if isinstance(scores[user], float)]
        guild_average_score = "{:.3}".format(sum(scores)/len(scores)) if scores else None
        return guild_average_score
    
    def sort_animelist_query_all(self, animelist_query: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        animelist_query = sorted(animelist_query, key=lambda entry: entry['titles']['title_english'].lower())
        query = [
            anime for anime in animelist_query if anime['jikan_response']['full']['data']['season']=='fall'
        ]+[
            anime for anime in animelist_query if anime['jikan_response']['full']['data']['season']=='summer'
        ]+[
            anime for anime in animelist_query if anime['jikan_response']['full']['data']['season']=='spring'
        ]+[
            anime for anime in animelist_query if anime['jikan_response']['full']['data']['season']=='winter'
        ]
        query = sorted(query, key=lambda entry: -entry['jikan_response']['full']['data']['year'])
        query += [
            anime for anime in animelist_query if not (anime['jikan_response']['full']['data']['season'] and anime['jikan_response']['full']['data']['year'])
        ]
        return query

    def parse_url_to_id(self, mal_url: str) -> int:
        search = re.findall('(?:myanimelist.net/anime/)(\d*)', mal_url)
        if len(search)!=1:
            raise ValueError('Invalid MAL URL')
        return int(search[0])
    
    def parse_day_time_to_broadcast(self, day: str, time: str) -> Dict[str, str]:
        
        day = day if day.endswith('s') else day+'s'
        if day not in self.weekdays:
            raise ValueError('Invalid weekday')
        time_components = [int(item) for item in time.split()]
        if (
            len(time_components)!=2 or
            int(time_components[0])>=28 or
            time_components[1]>=60
        ):
            raise ValueError('Invalid time')
        if time_components[0]>=24:
            day = self.weekdays[(self.weekdays.index(day)+1)%7]
            time_components = time_components-24
        time = f"{time_components[0]}:{time_components[1]}"
        for item in time_components:
            item = str(item)
            if len(item)!=2:
                item = '0'+item
        return {
            'day': day, 
            'time': time, 
            'timezone': 'Asia/Tokyo', 
            'string': f'{day} at {time} (JST)'
        }

    def parse_day(self, day: str) -> str:
        weekdays = ['Sundays', 'Mondays', 'Tuesdays', 'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays']
        day = day if day.endswith('s') else day+'s'
        if day not in weekdays:
            raise ValueError('Invalid weekday')
        return day
    
    def parse_time(self, time: str) -> List[int]:
        time_components = [int(item) for item in time.split(':')]
        if (
            len(time_components)!=2 or
            int(time_components[0])>=28 or
            time_components[1]>=60
        ):
            raise ValueError('Invalid time')
        return time_components

    def parse_day_time_to_broadcast(self, day: str, time_components: List[int]) -> Dict[str, str]:
        if time_components[0]>=24:
            day = self.weekdays[(self.weekdays.index(day)+1)%7]
            time_components[0] = time_components[0]-24
        for idx, item in enumerate(time_components):
            time_components[idx] = str(item)
            if len(str(item))!=2:
                time_components[idx] = '0'+str(item)
            time = f"{time_components[0]}:{time_components[1]}"
        return {
            'day': day, 
            'time': time, 
            'timezone': 'Asia/Tokyo', 
            'string': f'{day} at {time} (JST)'
        }
    
    def generate_notification_time(self, animelist_query: List[Dict[str, Any]]) -> List[datetime.time]:
        time_components_list = [
            anime['guild_data']['broadcast']['time'].split(':')
            for anime in animelist_query
        ]
        on_air_time: List[datetime.time] = [
            datetime.time(hour=int(components[0]), minute=int(components[1]))
            for components in time_components_list
            if len(components)==2
        ]
        extra_occuring_time = [
            (datetime.datetime.combine(datetime.date.today(), time) + datetime.timedelta(minutes=30)).time()
            for time in on_air_time
        ]
        extra_occuring_time += [
            (datetime.datetime.combine(datetime.date.today(), time) + datetime.timedelta(hours=1)).time()
            for time in on_air_time
        ]
        extra_occuring_time += [
            (datetime.datetime.combine(datetime.date.today(), time) + datetime.timedelta(hours=2)).time()
            for time in on_air_time
        ]
        return on_air_time+extra_occuring_time

    def generate_all_guild_query(self, bot: commands.Bot) -> Dict[str, Any]:
        animelist_query = []
        for guild in bot.guilds:
            try:
                animelist_query += database.animelist_query_all(guild=guild)
            except sqlite3.OperationalError:
                pass
        return animelist_query

    

database, utils = Database(), Utils()
            



class Anime(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.notification_loops = {}
        for guild in self.bot.guilds:
            try:
                animelist_entries = database.animelist_query_all(guild=guild)
            except sqlite3.OperationalError:
                continue
            for idx, entry in enumerate(animelist_entries):
                broadcast_time = entry['guild_data']['broadcast']['time'].split(':')
                self.notification_loops[f"{entry['mal_id']}@{guild.id}"] = Notification_Loop(
                    time=datetime.time(
                        hour=int(broadcast_time[0]),
                        minute=int(broadcast_time[1]),
                        tzinfo=datetime.timezone(datetime.timedelta(seconds=32400), 'Tokyo Standard Time')
                    ),
                    index=idx,
                    animelist_entry=entry,
                    guild=guild,
                    bot=self.bot
                )
        for loop in self.notification_loops:
            while not self.notification_loops[loop].is_running():
                print(f"Starting: {self.notification_loops[loop]}")
                self.notification_loops[loop].start()
        
        
    async def cog_load(self) -> None:
        # if not self.bot.is_ready():
        #     await self.bot.wait_until_ready()
        self.notification_loops = {}
        for guild in self.bot.guilds:
            try:
                animelist_entries = database.animelist_query_all(guild=guild)
            except sqlite3.OperationalError:
                continue
            for idx, entry in enumerate(animelist_entries):
                broadcast_time = entry['guild_data']['broadcast']['time'].split(':')
                self.notification_loops[f"{entry['mal_id']}@{guild.id}"] = Notification_Loop(
                    time=datetime.time(
                        hour=int(broadcast_time[0]),
                        minute=int(broadcast_time[1]),
                        tzinfo=datetime.timezone(datetime.timedelta(seconds=32400), 'Tokyo Standard Time')
                    ),
                    index=idx,
                    animelist_entry=entry,
                    guild=guild,
                    bot=self.bot
                )
                
        for loop in self.notification_loops:
            while not self.notification_loops[loop].is_running():
                print(f"Starting: {self.notification_loops[loop]}")
                self.notification_loops[loop].start()
                
        print(f"Extension loaded: {self.__class__.__name__}")
        return await super().cog_load()
    
    async def cog_unload(self) -> None:
        for loop in self.notification_loops:
            while self.notification_loops[loop].is_running():
                print(f"Cancelling: {self.notification_loops[loop]}")
                self.notification_loops[loop].cancel()
                await asyncio.sleep(0.3)
        print(f"Extension unloaded: {self.__class__.__name__}")
        return await super().cog_unload()
        

    anime = app_commands.Group(name='anime', description='Manage the server anime list!')

    @anime.command(name='setup', description='Setup this server for /anime.')
    async def setup(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        await database.setup_guild(guild=interaction.guild)
        await interaction.followup.send(content='Setup completed!')

    @anime.command(name='browse', description='Browse available titles on MyAnimeList.net.')
    @app_commands.describe(season='Search for a specific season.')
    async def browse(self, interaction: discord.Interaction, season: str = None):
        view = Browse_View(bot=self.bot, cog=self)
        if season:
            view.remove_item(view.select_season)
        await interaction.response.send_message(
            content=f"**{season}**" if season else None,
            view=view
        )
        original_response = await interaction.original_response()
        view.message = await original_response.fetch()

        if season:
            view.year = re.findall('\d{4}', season)[0]
            view.season = re.findall('Winter|Spring|Summer|Fall', season)[0]
            view.seasonal_animes = utils.get_season_shows_paged(year=int(view.year), season=view.season.lower())
            view.anime_page = 0
            view.select_anime.options = [
                discord.SelectOption(label=f"{anime['title_japanese']} ({anime['title_english']})"[:100], value=anime['mal_id'])
                for anime in view.seasonal_animes[view.anime_page]
            ]
            view.select_anime.disabled = False
            view.page_display.label = f"{view.anime_page+1}/{len(view.seasonal_animes)}"
            view.page_display.disabled = False
            view.next.disabled = False if len(view.seasonal_animes)!=1 else True
            await view.message.edit(view=view)

    @anime.command(name='add', description='Add an anime to the list.')
    async def add(self, interaction: discord.Interaction):
        modal = Add_Edit_Modal(title='Add Anime', bot=self.bot, cog=self)
        await interaction.response.send_modal(modal)
    
    @anime.command(name='edit', description='Edit an anime in the list.')
    @app_commands.describe(anime='Select an anime.')
    async def edit(self, interaction: discord.Interaction, anime: int):
        animelist_query = database.animelist_query_by_id(guild=interaction.guild, mal_id=anime)
        title = f"Edit Anime: {animelist_query['titles']['title_english']}"
        title = title if len(title)<=45 else title[:42]+'...'
        modal = Add_Edit_Modal(title=title, bot=self.bot, cog=self)
        modal.remove_item(item=modal.url)
        modal.url = animelist_query['jikan_response']['full']['data']['url']
        modal.weekday.default = animelist_query['guild_data']['broadcast']['day']
        modal.time.default = animelist_query['guild_data']['broadcast']['time']
        modal.external_links.default = animelist_query['guild_data']['links']
        await interaction.response.send_modal(modal)
        await modal.wait()
        

    @anime.command(name='remove', description='Remove an anime from the list.')
    @app_commands.describe(anime='Select an anime.')
    async def remove(self, interaction: discord.Interaction, anime: int):
        query = database.animelist_fast_query_by_id(guild=interaction.guild, mal_id=anime)
        execute = database.animelist_delete(guild=interaction.guild, mal_id=anime)
        await interaction.response.send_message(f"{query['titles']['title_english']} is removed from the list.")
        
    @anime.command(name='show', description='Show the info card of an anime.')
    @app_commands.describe(anime='Select an anime.')
    async def show(self, interaction: discord.Interaction, anime: int):
        animelist_query = database.animelist_query_by_id(guild=interaction.guild, mal_id=anime)
        config_query = database.config_query(guild=interaction.guild)
        thread_channel = discord.utils.get(interaction.guild.text_channels, id=config_query['threads'])
        thread = discord.utils.get(thread_channel.threads, id=animelist_query['guild_data']['thread'])

        embeds = [Card_Embed_Standard(animelist_query=animelist_query), Card_Embed_Scores(animelist_query=animelist_query)]
        view = Card_View(animelist_query=animelist_query, embeds=embeds, card_mode='Normal')
        view.remove_item(view.discussion), view.add_item(ui.Button(label='Discussion', url=thread.jump_url))
        view.remove_item(view.notification), view.add_item(view.notification)
        if animelist_query['guild_data']['notification']:
            view.notification.label = 'Notification: On'
            view.notification.style = discord.ButtonStyle.success
        else:
            view.notification.label = 'Notification: Off'
            view.notification.style = discord.ButtonStyle.secondary
        try:
            aired_to = datetime.datetime.fromisoformat(animelist_query['jikan_response']['full']['data']['aired']['to'])      
            if aired_to<datetime.datetime.now(aired_to.tzinfo):
                view.notification.disabled = True
        except (TypeError, ValueError):
            pass
            
        await interaction.response.send_message(embed=embeds[0], view=view)
        original_response = await interaction.original_response()
        view.message = await original_response.fetch()

    @anime.command(name='list', description='Show the server anime list.')
    async def list(self, interaction: discord.Interaction):
        animelist_query = database.animelist_query_all(guild=interaction.guild)
        animelist_query = utils.sort_animelist_query_all(animelist_query=animelist_query)
        animelist, idx = [], 1
        for anime in animelist_query:
            guild_average_score = utils.get_guild_average_score(scores=anime['guild_data']['scores'])
            animelist.append([
                idx, 
                anime['titles']['title_english'], 
                str(guild_average_score) if guild_average_score else '', 
                utils.get_anime_premiered_str(anime=anime['jikan_response']['full']), 
                ', '.join(utils.get_anime_studios(anime=anime['jikan_response']['full']))
            ])
            idx += 1
        animelist_paged, step = [], 8
        for i in range(0, len(animelist), step):
            animelist_paged.append(animelist[i:i+step])
        animelist_tables = []
        for page in animelist_paged:
            table = tabulate.tabulate(
                page, 
                headers=['#', 'Title', 'Score', 'Premiered', 'Studios'], 
                tablefmt='rounded_grid', 
                colalign=['right', 'left', 'left', 'left', 'left'],
                maxcolwidths=[3, 32, 5, 11, 12]
            )
            animelist_tables.append(table)
        
        
        view = List_View(animelist_tables=animelist_tables)
        view.title = f"{interaction.guild.name}'s Anime List"
        view.page_display.label = f'{view.current_page+1}/{view.max_page}'
        view.next.disabled = False if len(animelist_tables)>1 else True
        content = f'```{view.title}\n{animelist_tables[0][:1992-len(view.title)]}\n```'
        await interaction.response.send_message(content=content, view=view)
        original_response = await interaction.original_response()
        view.message = await original_response.fetch()
        
        


    @anime.command(name='schedule', description='Show the current anime schedule.')
    async def schedule(self, interaction: discord.Interaction):
        animelist_query = database.animelist_query_all(guild=interaction.guild)
        weekday_today = datetime.date.today().strftime('%A')
        embed = Schedule_Embed(animelist_query=animelist_query, weekday=f"{weekday_today}s")
        view = Schedule_View(weekday=f"{weekday_today}s", embeds={
            f"{day}s": Schedule_Embed(animelist_query=animelist_query, weekday=f"{day}s")
            for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        })
        for option in view.select_weekday.options:
            option.default = True if option.label==weekday_today else False
        await interaction.response.send_message(embed=embed, view=view)
        original_response = await interaction.original_response()
        view.message = await original_response.fetch()
        
    @anime.command(name='debug', description='⚠ Debugging purpose.')
    async def debug(self, interaction: discord.Interaction):
        # for loop in self.notification_loops:
        #     if not self.notification_loops[loop].is_running():
        #         print(f"Starting: {self.notification_loops[loop]}")
        #         self.notification_loops[loop].start()

        await interaction.response.defer(thinking=False)
        the_loops = [self.notification_loops[loop] for loop in self.notification_loops]
        print(self.notification_loops)
        for loop in the_loops:
            print(loop.is_running(), loop.time)
        




    @edit.autocomplete(name='anime')
    @remove.autocomplete(name='anime')
    @show.autocomplete(name='anime')
    async def anime_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        query = database.animelist_fast_query_all(guild=interaction.guild)
        choices = [app_commands.Choice(
            name=f"{entry['titles']['title_japanese']} ({entry['titles']['title_english']})"[:100], 
            value=entry['mal_id']
        ) for entry in query]
        return [title for title in choices if current.lower() in title.name.lower()][:25]
    
    @browse.autocomplete(name='season')
    async def season_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=season, value=season) for season in utils.seasons_str_cached
            if current.lower() in season.lower()
        ][:25]


    

class Notification_Loop(tasks.Loop):
    def __init__(
        self, 
        *, 
        time: Optional[List[datetime.time]], 
        index: int,
        animelist_entry: Dict[str, Any], 
        guild: discord.Guild, 
        bot: commands.Bot
    ) -> None:
        self.index, self.animelist_entry, self.guild, self.bot = index, animelist_entry, guild, bot
        super().__init__(self.coro, None, None, None, time, None, True)
    
    async def _before_loop(self) -> None:
        print(f"Loop for {self.guild.name} {self.animelist_entry['titles']['title_japanese']} starting...")
    
    async def _after_loop(self) -> None:
        print(f"Loop for {self.guild.name} {self.animelist_entry['titles']['title_japanese']} finishing...")
    
    async def coro(self, *args: Any, **kwargs: Any) -> Any:
        print(self)

        now, now_utc = datetime.datetime.now(), datetime.datetime.now(tz=datetime.timezone.utc)
        now_dict = {
            'day': now.strftime('%As'),
            'time': now.strftime('%H:%M'),
            'day_utc': now_utc.strftime('%As'),
            'time_utc': now_utc.strftime('%H:%M')
        }
        config_entry = database.config_query(guild=self.guild)
        episodes_channel = discord.utils.get(self.guild.text_channels, id=config_entry['episodes'])
        threads_channel = discord.utils.get(self.guild.text_channels, id=config_entry['threads'])
        thread = discord.utils.get(threads_channel.threads, id=self.animelist_entry['guild_data']['thread'])

        print(now, now_dict, episodes_channel.id, thread.id, thread.name)
        print(self.animelist_entry['guild_data']['broadcast']['time'], now_dict['time'])
        print(
            not self.animelist_entry['guild_data']['notification'] ,
            not self.animelist_entry['jikan_response']['full']['data']['airing'] ,
            self.animelist_entry['guild_data']['broadcast']['day']!=now_dict['day'] ,
            self.animelist_entry['guild_data']['broadcast']['time']!=now_dict['time']
        )
        

        if (
            not self.animelist_entry['guild_data']['notification'] or
            not self.animelist_entry['jikan_response']['full']['data']['airing'] or
            self.animelist_entry['guild_data']['broadcast']['day']!=now_dict['day'] or
            self.animelist_entry['guild_data']['broadcast']['time']!=now_dict['time']
        ):
            print('pass')
            pass
        else:
            content = f"{self.animelist_entry['titles']['title_english']} is live!"
            embeds = [Card_Embed_Standard(animelist_query=self.animelist_entry), Card_Embed_Scores(animelist_query=self.animelist_entry)]
            episodes_view = Card_View(embeds=embeds, animelist_query=self.animelist_entry, card_type='Overview', card_mode='Notification')
            threads_view = Card_View(embeds=embeds, animelist_query=self.animelist_entry, card_type='Overview', card_mode='Thread')
            threads_view.remove_item(threads_view.discussion)
            if self.animelist_entry['guild_data']['notification']:
                episodes_view.notification.label = 'Notification: On'
                episodes_view.notification.style = discord.ButtonStyle.success
                threads_view.notification.label = 'Notification: On'
                threads_view.notification.style = discord.ButtonStyle.success
            else:
                episodes_view.notification.label = 'Notification: Off'
                episodes_view.notification.style = discord.ButtonStyle.secondary
                threads_view.notification.label = 'Notification: Off'
                threads_view.notification.style = discord.ButtonStyle.secondary
            try:
                aired_to = datetime.datetime.fromisoformat(self.animelist_entry['jikan_response']['full']['data']['aired']['to'])      
                if aired_to<datetime.datetime.now(aired_to.tzinfo):
                    episodes_view.notification.disabled = True
                    threads_view.notification.disabled = True
            except (TypeError, ValueError):
                pass
            
            for member in thread.members:
                await thread.remove_user(member)
            
            episodes_view.message = await episodes_channel.send(content=content, embed=embeds[0], view=episodes_view)
            threads_view.message = await thread.send(content=content, embed=embeds[0], view=threads_view)
        
        await asyncio.sleep(self.index)
        jikan_response_full = jikan.anime(self.animelist_entry['mal_id'], extension='full')
        await asyncio.sleep(self.index)
        jikan_response_episodes = jikan.anime(self.animelist_entry['mal_id'], extension='episodes')
        if 'episodes' in self.animelist_entry['jikan_response']:
            new_episode = jikan_response_episodes['data']==self.animelist_entry['jikan_response']['episodes']['data']
        else:
            new_episode = False
        latest_episode = jikan_response_episodes['data'][-1] if jikan_response_episodes['data'] else None
        try:
            latest_episode_aired = datetime.datetime.fromisoformat(latest_episode['aired'])
        except:
            latest_episode_aired = None
        self.animelist_entry['jikan_response']['full'] = jikan_response_full
        self.animelist_entry['jikan_response']['episodes'] = jikan_response_episodes
        database.animelist_update(guild=self.guild, mal_id=self.animelist_entry['mal_id'], last_edited_by=self.bot.user, last_edited_on=now, jikan_response=self.animelist_entry['jikan_response'])

        if (
            not latest_episode_aired or
            (now_utc-latest_episode_aired)>=datetime.timedelta(days=7)
        ):
            thread_name = self.animelist_entry['titles']['title_english']
        else:
            thread_name = f"{self.animelist_entry['titles']['title_english']} - Episode {latest_episode['mal_id']}"
            # if new_episode:
            #     await thread.send(content=f"Latest episode: {latest_episode['mal_id']+1}")
        if thread.name!=thread_name:
            await thread.edit(name=thread_name)
            episode_no = re.findall('(?: - Episode )(\d+)$', thread_name)
            # if episode_no:
            #     await thread.send(content=f"Latest episode: {episode_no[0]}")
        
        print(latest_episode, thread_name)
            
        # if self._injected is not None:
        #     args = (self._injected, *args)

        # return await self.coro(*args, **kwargs)
        
class Card_Embed_Preview(discord.Embed):
    def __init__(self, *, jikan_response: Dict[str ,Any]):
        color = 3035554
        title = utils.get_anime_titles(anime=jikan_response['full'])['title_japanese']
        description = f"`{utils.get_anime_titles(anime=jikan_response['full'])['title_english']}`"
        
        score = jikan_response['full']['data']['score']
        premiered = f"{jikan_response['full']['data']['season'].capitalize()} {jikan_response['full']['data']['year']}"
        broadcast = jikan_response['full']['data']['broadcast']['string']
        studios = ', '.join([studio['name'] for studio in jikan_response['full']['data']['studios']])
        self.add_field(
            name='Overview',
            value=f"""
Score: `MAL {score}`
Premiered: `{premiered}`
On Air: `{broadcast}`
Studios: `{studios}`
            """,
            inline=False
        )

        official_site_url = [link['url'] for link in jikan_response['full']['data']['external'] if link['name'] == 'Official Site']
        official_site_url = f"[Official Site]({official_site_url[0]})" if official_site_url else None
        mal_url = f"[MyAnimeList]({jikan_response['full']['data']['url']})"
        links = f"{official_site_url}\n{mal_url}" if official_site_url else mal_url
        self.add_field(
            name='Links',
            value=links,
            inline=True
        )

        self.set_image(url=utils.get_anime_image_jpg(anime=jikan_response['full']))
        
        super().__init__(color=3035554, title=title, description=description)
    

class Card_View_Preview(ui.View):
    def __init__(
        self, *, timeout: Optional[float] = None, 
        jikan_response: Dict[str ,Any], 
        message: discord.Message = None, 
        bot: commands.Bot = None,
        cog: Anime = None
    ):
        super().__init__(timeout=timeout)
        self.jikan_response, self.message, self.bot, self.cog = jikan_response, message, bot, cog

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        
    @ui.button(style=discord.ButtonStyle.primary, label='Add')
    async def add(self, interaction: discord.Interaction, button: ui.Button):
        modal = Add_Edit_Modal(bot=self.bot, cog=self.cog)
        modal.title = f"Add Anime: {utils.get_anime_titles(anime=self.jikan_response['full'])['title_english']}"
        modal.title = modal.title if len(modal.title)<=45 else modal.title[:42]+'...'
        modal.remove_item(modal.url)
        modal.url = self.jikan_response['full']['data']['url']
        modal.weekday.default = self.jikan_response['full']['data']['broadcast']['day']
        modal.time.default = self.jikan_response['full']['data']['broadcast']['time']
        await interaction.response.send_modal(modal)
        original_response = await interaction.original_response()

        await modal.wait()
        view = Card_View_Preview(jikan_response=self.jikan_response, message=await original_response.fetch(), bot=self.bot, cog=self.cog)
        view.remove_item(view.add)
        view.add_item(ui.Button(label='Browser', url=self.jikan_response['full']['data']['url']))
        await view.message.edit(view=view)
    
    @ui.button(style=discord.ButtonStyle.danger, label='Remove')
    async def remove(self, interaction: discord.Interaction, button: ui.Button):
        content = f"{interaction.user.mention} Remove: {utils.get_anime_titles(self.jikan_response['full'])['title_english']}?"
        view = Remove_View(jikan_response=self.jikan_response, card_message=self.message, bot=self.bot)
        await interaction.response.send_message(content=content, view=view)
        original_response = await interaction.original_response()
        view.message = await original_response.fetch()
    
    @ui.button(style=discord.ButtonStyle.secondary, label='Close')
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await self.message.delete()
    
class Card_Embed_Standard(discord.Embed):
    def __init__(self, *, animelist_query: Dict[str ,Any]):
        color = 3035554
        title = animelist_query['titles']['title_japanese']
        description = f"`{animelist_query['titles']['title_english']}`"

        score = animelist_query['jikan_response']['full']['data']['score']
        guild_score = utils.get_guild_average_score(scores=animelist_query['guild_data']['scores'])
        premiered = utils.get_anime_premiered_str(anime=animelist_query['jikan_response']['full'])
        broadcast = animelist_query['guild_data']['broadcast']['string']
        studios = ', '.join([studio['name'] for studio in animelist_query['jikan_response']['full']['data']['studios']])
        self.add_field(
            name='Overview',
            value=f"""
Score: `MAL {score}` | `Server {guild_score}`
Premiered: `{premiered}`
On Air: `{broadcast}`
Studios: `{studios}`
            """,
            inline=False
        )

        official_site_url = [link['url'] for link in animelist_query['jikan_response']['full']['data']['external'] if link['name'] == 'Official Site']
        official_site_url = f"[Official Site]({official_site_url[0]})" if official_site_url else None
        mal_url = f"[MyAnimeList]({animelist_query['jikan_response']['full']['data']['url']})"
        links = f"{official_site_url}\n{mal_url}" if official_site_url else mal_url
        self.add_field(
            name='Links',
            value=links,
            inline=True
        )

        guild_links = animelist_query['guild_data']['links']
        if re.findall('\[.*\]\(.*\)', animelist_query['guild_data']['links']):
            self.add_field(
                name='External Links',
                value=guild_links,
                inline=True
            )

        self.set_image(url=utils.get_anime_image_jpg(anime=animelist_query['jikan_response']['full']))
        
        super().__init__(color=3035554, title=title, description=description)

class Card_Embed_Scores(discord.Embed):
    def __init__(self, *, animelist_query: Dict[str ,Any]):
        color = 3035554
        title = animelist_query['titles']['title_japanese']
        description = f"`{animelist_query['titles']['title_english']}`"

        self.set_thumbnail(url=utils.get_anime_image_jpg(anime=animelist_query['jikan_response']['full']))

        guild_scores_str = '\n'.join([
            f"<@{user}>: `{animelist_query['guild_data']['scores'][user]}`"
            for user in animelist_query['guild_data']['scores']
            if animelist_query['guild_data']['scores'][user]
        ])
        average_score_str = f"Average: `{utils.get_guild_average_score(scores=animelist_query['guild_data']['scores'])}`"
        self.add_field(
            name='Server Scores',
            value=f"{guild_scores_str if guild_scores_str else '`None`'}\nー\n{average_score_str}"
        )
        
        super().__init__(color=3035554, title=title, description=description)




class Card_View(ui.View):
    def __init__(
        self, *, timeout: Optional[float] = None, 
        embeds: List[discord.Embed], 
        animelist_query: Dict[str, Any], 
        message: discord.Message = None, 
        card_type: Literal['Overview', 'Scores'] = 'Overview',
        card_mode: Literal['Normal', 'Notification', 'Thread'] = 'Normal'
    ):
        super().__init__(timeout=timeout)
        self.embeds, self.animelist_query, self.message, self.card_type, self.card_mode = embeds, animelist_query, message, card_type, card_mode
        self.current_page = 0
        self.page.options[0].default=True if self.card_type == 'Overview' else False
        self.page.options[1].default=True if self.card_type == 'Scores' else False

    @ui.select(placeholder='Select a page', options=[
        discord.SelectOption(label='Overview', value=0),
        discord.SelectOption(label='Scores', value=1)
    ])
    async def page(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.defer(thinking=False)
        if select.values[0]=='0':
            self.card_type = 'Overview'
            embed = self.embeds[0]
            select.options = [
                discord.SelectOption(label='Overview', value=0, default=True),
                discord.SelectOption(label='Scores', value=1)
            ]
        elif select.values[0]=='1':
            self.card_type = 'Scores'
            embed = self.embeds[1]
            select.options = [
                discord.SelectOption(label='Overview', value=0),
                discord.SelectOption(label='Scores', value=1, default=True)
            ]
        await self.message.edit(embed=embed, view=self)
    
    @ui.button(label='Score', style=discord.ButtonStyle.primary)
    async def score(self, interaction: discord.Interaction, button: ui.Button):
        content = f"{interaction.user.mention} Rate: **{self.animelist_query['titles']['title_english']}**"
        view = Score_View(animelist_query=self.animelist_query, card_message=self.message, card_type=self.card_type, card_mode=self.card_mode)
        await interaction.response.send_message(content=content, view=view)
        original_response = await interaction.original_response()
        view.message = await original_response.fetch()

    @ui.button(label='Discussion', style=discord.ButtonStyle.primary)
    async def discussion(self, interaction: discord.Interaction, button: ui.Button):
        config_query = database.config_query(guild=interaction.guild)
        thread_channel = discord.utils.get(interaction.guild.text_channels, id=config_query['threads'])
        thread = discord.utils.get(thread_channel.threads, id=self.animelist_query['guild_data']['thread'])
        await thread.add_user(interaction.user)
        view = ui.View()
        view.add_item(ui.Button(label='Enter Thread', url=thread.jump_url))
        await interaction.response.send_message(view=view, ephemeral=True)

    @ui.button(label='Notification: Off', style=discord.ButtonStyle.secondary)
    async def notification(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        if self.animelist_query['guild_data']['notification']:
            self.animelist_query['guild_data']['notification'] = False
            database.animelist_update(
                guild=interaction.guild,
                mal_id=self.animelist_query['mal_id'],
                last_edited_by=interaction.user,
                last_edited_on=datetime.datetime.now(),
                guild_data=self.animelist_query['guild_data']
            )
            button.label, button.style = 'Notification: Off', discord.ButtonStyle.secondary
        else:
            self.animelist_query['guild_data']['notification'] = True
            database.animelist_update(
                guild=interaction.guild,
                mal_id=self.animelist_query['mal_id'],
                last_edited_by=interaction.user,
                last_edited_on=datetime.datetime.now(),
                guild_data=self.animelist_query['guild_data']
            )
            button.label, button.style = 'Notification: On', discord.ButtonStyle.success
        await self.message.edit(view=self)
        self.animelist_query = database.animelist_query_by_id(guild=interaction.guild, mal_id=self.animelist_query['mal_id'])

class Schedule_Embed(discord.Embed):
    def __init__(
        self, *, color: Optional[int] = 3035554, title: Optional[Any] = 'On Air Schedule', 
        animelist_query: List[Dict[str, Any]], 
        weekday: Literal['Sundays', 'Mondays', 'Tuesdays', 'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays']
    ):
        animelist_query = [
            anime for anime in animelist_query 
            if anime['guild_data']['broadcast']['day']==weekday and
            anime['jikan_response']['full']['data']['airing']
        ]
        animelist = []
        for anime in animelist_query:
            animelist.append([anime['guild_data']['broadcast']['time'], anime['titles']['title_english']])
        animelist = sorted(animelist, key=lambda anime: anime[0])
        table = tabulate.tabulate(
            tabular_data=animelist,
            tablefmt='rounded_grid',
            maxcolwidths=[5, 49]
        ) if animelist else None
        description = f"```\n{table}\n```"
        super().__init__(color=color, title=title, description=description)
    
class Schedule_View(ui.View):
    def __init__(
        self, *, timeout: Optional[float] = None, 
        weekday: Literal['Sundays', 'Mondays', 'Tuesdays', 'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays'], 
        embeds = Dict[Literal['Sundays', 'Mondays', 'Tuesdays', 'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays'], Schedule_Embed], 
        message: discord.Message = None
    ):
        super().__init__(timeout=timeout)
        self.weekday, self.embeds, self.message = weekday, embeds, message
    
    @ui.select(
        placeholder='Select a weekday', 
        options=[
            discord.SelectOption(label=day)
            for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        ]
    )
    async def select_weekday(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.defer()
        self.weekday = f"{select.values[0]}s"
        embed = self.embeds[self.weekday]
        for option in select.options:
            option.default = True if option.value==select.values[0] else False
        await self.message.edit(embed=embed, view=self)


    

    
    


class Browse_View(ui.View):
    def __init__(
        self, *, timeout: Optional[float] = None, 
        message: discord.Message = None, 
        card_message: discord.Message = None, 
        bot: commands.Bot = None,
        cog: Anime = None
    ):
        super().__init__(timeout=timeout)
        self.message, self.card_message, self.bot, self.cog = message, card_message, bot, cog
        #self.year, self.season
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
    
    @ui.select(
        placeholder='Select a season', 
        options=[discord.SelectOption(label=season) for season in utils.get_seasons_str()][:25],
        row=0
    )
    async def select_season(self, interaction: discord.Interaction, select: ui.Select):
        self.select_anime.disabled = True
        select.options = [discord.SelectOption(
            label=season,
            default=True if season == select.values[0] else False
        ) for season in utils.get_seasons_str()][:25]
        await self.message.edit(view=self)
        await interaction.response.defer(thinking=False)

        self.year = re.findall('\d{4}', select.values[0])[0]
        self.season = re.findall('Winter|Spring|Summer|Fall', select.values[0])[0]
        self.seasonal_animes = utils.get_season_shows_paged(year=int(self.year), season=self.season.lower())
        self.anime_page = 0
        self.select_anime.options = [
            discord.SelectOption(label=f"{anime['title_japanese']} ({anime['title_english']})"[:100], value=anime['mal_id'])
            for anime in self.seasonal_animes[self.anime_page]
        ]
        self.select_anime.disabled = False
        self.page_display.label = f"{self.anime_page+1}/{len(self.seasonal_animes)}"
        self.page_display.disabled = False
        self.next.disabled = False if len(self.seasonal_animes)!=1 else True
        await self.message.edit(view=self)
        
    
    @ui.select(placeholder='Select an anime', options=[discord.SelectOption(label='None')], disabled=True, row=1)
    async def select_anime(self, interaction: discord.Interaction, select: ui.Select):
        select.options = [
            discord.SelectOption(
                label=f"{anime['title_japanese']} ({anime['title_english']})"[:100], 
                value=anime['mal_id'],
                default=True if str(anime['mal_id'])==select.values[0] else False
            )
            for anime in self.seasonal_animes[self.anime_page]
        ]
        await self.message.edit(view=self)
        jikan_response = {'full': jikan.anime(select.values[0], extension='full')}
        embed = Card_Embed_Preview(jikan_response=jikan_response)
        view = Card_View_Preview(jikan_response=jikan_response, bot=self.bot, cog=self.cog)
        if not database.animelist_fast_query_by_id(guild=interaction.guild, mal_id=jikan_response['full']['data']['mal_id']):
            view.remove_item(view.remove)
        else:
            view.remove_item(view.add)
        view.add_item(ui.Button(label='Browser', url=jikan_response['full']['data']['url']))
        if not self.card_message:
            await interaction.response.send_message(embed=embed, view=view)
            original_response = await interaction.original_response()
            self.card_message = view.message = await original_response.fetch()
            return
        try:
            view.message = await self.card_message.edit(embed=embed, view=view)
            await interaction.response.defer(thinking=False)
        except discord.errors.NotFound:
            await interaction.response.send_message(embed=embed, view=view)
            original_response = await interaction.original_response()
            self.card_message = view.message = await original_response.fetch()

    @ui.button(label='< Previous', disabled=True, style=discord.ButtonStyle.blurple, row=2)
    async def previous(self, interaction: discord.Interaction, button: ui.Button):
        self.anime_page -= 1
        shows_paged = self.seasonal_animes[self.anime_page]
        
        self.select_anime.options = [
            discord.SelectOption(label=f"{anime['title_japanese']} ({anime['title_english']})"[:100], value=anime['mal_id'])
            for anime in shows_paged
        ]
        self.next.disabled = False
        self.page_display.label = f"{self.anime_page+1}/{len(self.seasonal_animes)}"
        if self.anime_page==0:
            button.disabled = True
        await self.message.edit(view=self)
        await interaction.response.defer(thinking=False)
        
    @ui.button(label='-/-', disabled=True, style=discord.ButtonStyle.gray, row=2)
    async def page_display(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(thinking=False)
    
    @ui.button(label='Next >', disabled=True, style=discord.ButtonStyle.blurple, row=2)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        self.anime_page += 1
        shows_paged = self.seasonal_animes[self.anime_page]
        self.select_anime.options = [
            discord.SelectOption(label=f"{anime['title_japanese']} ({anime['title_english']})"[:100], value=anime['mal_id'])
            for anime in shows_paged
        ]
        self.previous.disabled = False
        self.page_display.label = f"{self.anime_page+1}/{len(self.seasonal_animes)}"
        if self.anime_page+1==len(self.seasonal_animes):
            button.disabled = True
        await self.message.edit(view=self)
        await interaction.response.defer(thinking=False)

    @ui.button(label='Close', style=discord.ButtonStyle.gray, row=2)
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await self.message.delete()
        try:
            await self.card_message.delete()
        except (AttributeError, discord.errors.NotFound):
            pass

    @ui.button(label='?', style=discord.ButtonStyle.gray, row=2)
    async def help(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(content='For earlier seasons, manually input with `/anime browse season:`', ephemeral=True)




class Remove_View(ui.View):
    def __init__(
        self, *, timeout: Optional[float] = None, 
        jikan_response: Dict[str, Any], 
        bot: commands.Bot = None,
        message: discord.Message = None, 
        card_message: discord.Message,
    ):
        self.jikan_response = jikan_response
        self.bot = bot
        self.message, self.card_message = message, card_message
        super().__init__(timeout=timeout)
    
    @ui.button(label='Remove', style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: ui.Button):
        database.animelist_delete(guild=interaction.guild, mal_id=self.jikan_response['full']['data']['mal_id'])
        view = Card_View_Preview(jikan_response=self.jikan_response, message=self.card_message, bot=self.bot)
        view.remove_item(view.remove)
        view.add_item(ui.Button(label='Browser', url=self.jikan_response['full']['data']['url']))
        await self.card_message.edit(view=view)
        content = f"{utils.get_anime_titles(anime=self.jikan_response['full'])['title_english']} is removed from the list."
        await self.card_message.reply(content=content)
        await self.message.delete()
    
    @ui.button(label='Cancel', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await self.message.delete()
    
class Score_View(ui.View):
    def __init__(
        self, *, timeout: Optional[float] = None, 
        animelist_query: Dict[str, Any], 
        message: discord.Message = None, 
        card_message: discord.Message, 
        card_type: Literal['Overview', 'Scores'] = None,
        card_mode: Literal['Normal', 'Notification', 'Thread'] = None
    ):
        self.animelist_query, self.message, self.card_message, self.card_type, self.card_mode = animelist_query, message, card_message, card_type, card_mode
        super().__init__(timeout=timeout)
    
    @ui.select(placeholder='Select a score', options=[
        discord.SelectOption(
            label=str(x/2).replace('.0', ''),
            value=str(x/2)
        ) for x in range(20, -1, -1)
    ]+[discord.SelectOption(label='None')])
    async def select_score(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.defer(thinking=False)
    
    @ui.button(label='Submit', style=discord.ButtonStyle.primary)
    async def submit(self, interaction: discord.Interaction, button: discord.Button):
        score = None if self.select_score.values[0]=='None' else float(self.select_score.values[0])
        self.animelist_query['guild_data']['scores'][interaction.user.id] = score
        execute = database.animelist_update(
            guild=interaction.guild, 
            mal_id=self.animelist_query['mal_id'],
            last_edited_by=interaction.user, 
            last_edited_on=datetime.datetime.now(),
            guild_data=self.animelist_query['guild_data']
        )
        await self.message.delete()
        content = f"{interaction.user.mention} rated {self.animelist_query['titles']['title_english']} {str(score).replace('.0', '')}!"
        content = content if score else f"{interaction.user.mention} removed their score on {self.animelist_query['titles']['title_english']}."
        await self.card_message.reply(content=content)
        self.animelist_query = database.animelist_query_by_id(guild=interaction.guild, mal_id=self.animelist_query['mal_id'])
        self.config_query = database.config_query(guild=interaction.guild)
        self.thread_channel = discord.utils.get(interaction.guild.text_channels, id=self.config_query['threads'])
        self.thread = discord.utils.get(self.thread_channel.threads, id=self.animelist_query['guild_data']['thread'])
        if self.card_type=='Overview':
            embed = Card_Embed_Standard(animelist_query=self.animelist_query)
            embeds = [embed, Card_Embed_Scores(animelist_query=self.animelist_query)]
        elif self.card_type=='Scores':
            embed = Card_Embed_Scores(animelist_query=self.animelist_query)
            embeds = [Card_Embed_Standard(animelist_query=self.animelist_query), embed]
        view = Card_View(embeds=embeds, animelist_query=self.animelist_query, message=self.card_message, card_type=self.card_type, card_mode=self.card_mode)
        if self.card_mode=='Normal':
            view.remove_item(view.discussion), view.add_item(ui.Button(label='Discussion', url=self.thread.jump_url))
            view.remove_item(view.notification), view.add_item(view.notification)
        if self.card_mode=='Thread':
            view.remove_item(view.discussion)
        if self.animelist_query['guild_data']['notification']:
            view.notification.label = 'Notification: On'
            view.notification.style = discord.ButtonStyle.success
        else:
            view.notification.label = 'Notification: Off'
            view.notification.style = discord.ButtonStyle.success
        try:
            aired_to = datetime.datetime.fromisoformat(self.animelist_query['jikan_response']['full']['data']['aired']['to'])      
            if aired_to<datetime.datetime.now(aired_to.tzinfo):
                view.notification.disabled = True
        except (TypeError, ValueError):
            pass
        await self.card_message.edit(embed=embed, view=view)
    
    @ui.button(label='Cancel')
    async def cancel(self, interaction: discord.Interaction, button: discord.Button):
        await self.message.delete()
    
class List_View(ui.View):
    def __init__(
        self, *, timeout: Optional[float] = None,
        message: discord.Message = None,
        animelist_tables: List[str]
    ):
        self.message, self.animelist_tables = message, animelist_tables
        self.title = None
        self.current_page, self.max_page = 0, len(animelist_tables)
        super().__init__(timeout=timeout)
    
    @ui.button(style=discord.ButtonStyle.primary, label='< Previous', disabled=True)
    async def previous(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.current_page -= 1
        button.disabled = True if self.current_page==0 else False
        self.page_display.label = f'{self.current_page+1}/{self.max_page}'
        self.next.disabled = False
        await self.message.edit(content=f'```{self.title}\n{self.animelist_tables[self.current_page][:1992-len(self.title)]}\n```', view=self)
    
    @ui.button(label='-/-')
    async def page_display(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
    
    @ui.button(style=discord.ButtonStyle.primary, label='Next >')
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.current_page += 1
        self.previous.disabled = False
        self.page_display.label = f'{self.current_page+1}/{self.max_page}'
        button.disabled = True if self.current_page==self.max_page-1 else False
        await self.message.edit(content=f'```{self.title}\n{self.animelist_tables[self.current_page][:1992-len(self.title)]}\n```', view=self)



class Add_Edit_Modal(ui.Modal):
    def __init__(
        self, *, title: str = 'Edit Anime', timeout: Optional[float] = 600,
        bot: commands.Bot = None,
        cog: Anime = None
    ) -> None:
        self.bot, self.cog = bot, cog
        super().__init__(title=title, timeout=timeout)
    
    url = ui.TextInput(
        label='MyAnimeList URL', 
        placeholder='https://myanimelist.net/anime/...',
    )
    weekday = ui.TextInput(
        label='On Air Weekday (JST)', 
        placeholder='e.g. Sundays', 
        max_length=10, 
        min_length=6
    )
    time = ui.TextInput(
        label='On Air Time (JST)', 
        placeholder='e.g. 00:30', 
        max_length=5, 
        min_length=5
    )
    external_links = ui.TextInput(
        label='External Links', 
        placeholder='''e.g. 
[Netflix](https://www.netflix.com/...)
[Prime Video](https://www.amazon.co.jp/...)''', 
        required=False, 
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        emojis = {e.name:str(e) for e in interaction.client.emojis}
        now = datetime.datetime.now()
        try:
            if isinstance(self.url, ui.TextInput):
                mal_id = utils.parse_url_to_id(mal_url=self.url.value)
            elif isinstance(self.url, str):
                print(self.url)
                mal_id = utils.parse_url_to_id(mal_url=self.url)
        except ValueError:
            await interaction.response.send_message(content=f"Invalid URL {emojis['majj']}", ephemeral=True)
            return
        try:
            day = utils.parse_day(day=self.weekday.value)
        except ValueError:
            await interaction.response.send_message(content=f"Invalid weekday {emojis['majj']}", ephemeral=True)
            return
        try:
            time_components = utils.parse_time(time=self.time.value)
        except ValueError:
            await interaction.response.send_message(content=f"Invalid time {emojis['majj']}", ephemeral=True)
            return
        
        jikan_response = {'full': jikan.anime(id=mal_id, extension='full')}
        broadcast = utils.parse_day_time_to_broadcast(day=day, time_components=time_components)

        animelist_query = database.animelist_query_by_id(guild=interaction.guild, mal_id=mal_id)
        config_query = database.config_query(interaction.guild)
        
        if config_query:
            thread_channel = discord.utils.get(interaction.guild.text_channels, id=config_query['threads'])
        else:
            await interaction.response.send_message(
                content='Setup the server first with `/anime setup`', 
                ephemeral=True
            )
            return
        
        if not animelist_query:
            thread_message = await thread_channel.send(
                content=f"{utils.get_anime_titles(anime=jikan_response['full'])['title_english']} is added to the list!"
            )
            thread = await thread_message.create_thread(
                name=utils.get_anime_titles(anime=jikan_response['full'])['title_english'],
                auto_archive_duration=10080
            )
            execute = database.animelist_insert(
                guild=interaction.guild, 
                added_by=interaction.user, 
                added_on=now, 
                jikan_response={'full': jikan_response['full']},
                guild_data={
                    'scores': {},
                    'broadcast': broadcast,
                    'links': self.external_links.value,
                    'thread': thread.id,
                    'notification': True
                }
            )
        else:
            thread = discord.utils.get(thread_channel.threads, id=animelist_query['guild_data']['thread'])
            if not thread:
                thread_message = await thread_channel.send(
                    content=f"{utils.get_anime_titles(anime=jikan_response['full'])['title_english']} is added to the list!"
                )
                thread = await thread_message.create_thread(
                    name=utils.get_anime_titles(anime=jikan_response['full'])['title_english'],
                    auto_archive_duration=10080
                )
            animelist_query['jikan_response']['full'] = jikan_response['full']
            animelist_query['guild_data']['broadcast'] = broadcast
            animelist_query['guild_data']['links'] = self.external_links.value
            execute = database.animelist_update(
                guild=interaction.guild,
                mal_id=mal_id,
                last_edited_by=interaction.user,
                last_edited_on=now,
                jikan_response=animelist_query['jikan_response'],
                guild_data=animelist_query['guild_data']
            )
        
        if execute=='INSERT':
            content = f"{utils.get_anime_titles(anime=jikan_response['full'])['title_english']} is added to the list!"
        elif execute=='UPDATE':
            content = f"{utils.get_anime_titles(anime=jikan_response['full'])['title_english']} is updated!"
        
        animelist_query = database.animelist_query_by_id(guild=interaction.guild, mal_id=mal_id)
        embeds = [Card_Embed_Standard(animelist_query=animelist_query), Card_Embed_Scores(animelist_query=animelist_query)]
        view = Card_View(animelist_query=animelist_query, embeds=embeds)
        view.remove_item(view.discussion), view.add_item(ui.Button(label='Discussion', url=thread.jump_url))
        view.remove_item(view.notification), view.add_item(view.notification)
        if animelist_query['guild_data']['notification']:
            view.notification.label = 'Notification: On'
            view.notification.style = discord.ButtonStyle.success
        else:
            view.notification.label = 'Notification: Off'
            view.notification.style = discord.ButtonStyle.secondary
        try:
            aired_to = datetime.datetime.fromisoformat(animelist_query['jikan_response']['full']['data']['aired']['to'])      
            if aired_to<datetime.datetime.now(aired_to.tzinfo):
                view.notification.disabled = True
        except (TypeError, ValueError):
            pass
        await interaction.response.send_message(content=content, embed=embeds[0], view=view)
        original_response = await interaction.original_response()
        view.message = await original_response.fetch()

        if self.cog:
            broadcast_time = animelist_query['guild_data']['broadcast']['time'].split(':')
            if f"{animelist_query['mal_id']}@{interaction.guild.id}" in self.cog.notification_loops:
                notification_loop = self.cog.notification_loops[f"{animelist_query['mal_id']}@{interaction.guild.id}"]
                # notification_loop.cancel()
                notification_loop.change_interval(time=datetime.time(
                    hour=int(broadcast_time[0]),
                    minute=int(broadcast_time[1]),
                    tzinfo=datetime.timezone(datetime.timedelta(seconds=32400), 'Tokyo Standard Time')
                ))
                notification_loop.animelist_entry = animelist_query
            else:
                notification_loop = Notification_Loop(
                    time=[datetime.time(
                        hour=int(broadcast_time[0]),
                        minute=int(broadcast_time[1]),
                        tzinfo=datetime.timezone(datetime.timedelta(seconds=32400), 'Tokyo Standard Time')
                    )],
                    index=len(self.cog.notification_loops),
                    animelist_entry=animelist_query,
                    guild=interaction.guild,
                    bot=self.bot
                )
                self.cog.notification_loops[f"{animelist_query['mal_id']}@{interaction.guild.id}"] = notification_loop
            while notification_loop.is_running():
                notification_loop.cancel()
                await asyncio.sleep(1)
            notification_loop.start()

        return await super().on_submit(interaction)