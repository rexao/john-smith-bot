import discord
from discord import app_commands, ui
from discord.ext import commands

import datetime
import logging
import re
import sqlite3
from typing import Optional

logger = logging.getLogger('discord')


def stats_db_emotes_table_secure(c: sqlite3.Cursor, guild_id):
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS emotes_{guild_id} (
            emote_code VARCHAR,
            usage INT,
            debut_date BLOB,
            last_used BLOB
        )
    """)

def stats_db_emotes_row_secure(c: sqlite3.Cursor, guild_id, emote_code):
    c.execute(f"""
        SELECT emote_code
        FROM emotes_{guild_id}
    """)
    if emote_code in [code[0] for code in c.fetchall()]:
        return
    c.execute(f"""
        INSERT INTO emotes_{guild_id}
        VALUES (?, ?, ?, ?)
    """, (emote_code, 0, datetime.datetime.now(), datetime.datetime.now()))
    return

def stats_db_emotes_update_increment(guild_id, emote_code, timestamp: datetime.datetime):
    db = sqlite3.connect('stats.db')
    c = db.cursor()
    stats_db_emotes_table_secure(c, guild_id)
    stats_db_emotes_row_secure(c, guild_id, emote_code)
    c.execute(f"""
        UPDATE emotes_{guild_id}
        SET usage = usage + 1, last_used = ?
        WHERE emote_code = ?
    """, (timestamp, emote_code,))
    db.commit()
    db.close()
    return 'UPDATE'

def stats_db_emotes_update(guild_id, emote_code, usage, debut_date = None, last_used = None):
    db = sqlite3.connect('stats.db')
    c = db.cursor()
    stats_db_emotes_table_secure(c, guild_id)
    stats_db_emotes_row_secure(c, guild_id, emote_code)
    c.execute(f"""
        UPDATE emotes_{guild_id}
        SET usage = ?
        WHERE emote_code = ?
    """, (usage, emote_code,))
    if debut_date:
        c.execute(f"""
            UPDATE emotes_{guild_id}
            SET debut_date = ?
            WHERE emote_code = ?
        """, (debut_date, emote_code,))
    if last_used:
        c.execute(f"""
            UPDATE emotes_{guild_id}
            SET last_used = ?
            WHERE emote_code = ?
        """, (last_used, emote_code,))
    db.commit()
    db.close()
    return 'UPDATE'


def stats_db_emotes_query_order_by_usage(guild_id):
    db = sqlite3.connect('stats.db')
    c = db.cursor()
    stats_db_emotes_table_secure(c, guild_id)
    c.execute(f"""
        SELECT * FROM emotes_{guild_id}
        ORDER BY usage DESC, debut_date ASC
    """)
    entries = c.fetchall()
    results = []
    for entry in entries:
        results.append({
            "emote_code" : entry[0],
            "usage" : entry[1],
            "debut_date" : entry[2],
            "last_used" : entry[3]
        })
    db.close()
    return results


def stats_emotes_discord_code_appendage(query: list, emojis: dict):
    for entry in query:
        if entry['emote_code'].replace(':', '') in emojis:
            entry['discord_emote_code'] = emojis[entry['emote_code'].replace(':', '')]
    return [entry for entry in query if 'discord_emote_code' in entry]

def stats_emotes_content_generation(query: list, show_per_page: int = 25):
    x, y = len(query), show_per_page
    max_page = int(x//y+(x%y)/(x%y) if x%y!=0 else x//y)

    content_pages = []
    for idx in range(0, max_page): #0:24, 25:49, 50:74, 75:99, ...
        i = idx*y+1
        content = ''
        for entry in query[idx*y:(idx+1)*y]:
            content += f"`{i}`　-　{entry['discord_emote_code']} {entry['emote_code'].replace(':', '')}　-　{entry['usage']}\n"
            i += 1
        content_pages.append(content)
    
    return content_pages
            
def stats_emotes_embed_generation(interaction: discord.Interaction, content_pages: list, page: int = 1):
    embed = discord.Embed(
        color=15158332,
        title=f"Top Emotes",
        description=content_pages[page-1] if content_pages[page-1] else 'None',
        timestamp=datetime.datetime.now()
    )
    embed.set_author(
        name=interaction.guild.name, 
        icon_url=interaction.guild.icon
    )
    return embed


def stats_db_chatters_table_secure(c: sqlite3.Cursor, guild_id: int):
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS chatters_{guild_id} (
            user_id INT,
            total_messages_sent INT,
            first_message_datetime BLOB,
            latest_message_datetime BLOB
        )
    """)

def stats_db_chatters_row_secure(c: sqlite3.Cursor, guild_id: int, user_id: int):
    c.execute(f"""
        SELECT user_id
        FROM chatters_{guild_id}
    """)
    if user_id in [id[0] for id in c.fetchall()]:
        return
    
    now = datetime.datetime.now()
    c.execute(f"""
        INSERT INTO chatters_{guild_id}
        VALUES (?, ?, ?, ?)
    """, (user_id, 0, now, now))

def stats_db_chatters_update_increment(guild_id: int, user_id: int, timestamp: datetime.datetime):
    db = sqlite3.connect('stats.db')
    c = db.cursor()
    stats_db_chatters_table_secure(c, guild_id)
    stats_db_chatters_row_secure(c, guild_id, user_id)
    c.execute(f"""
        UPDATE chatters_{guild_id}
        SET total_messages_sent = total_messages_sent + 1, latest_message_datetime = ?
        WHERE user_id = ?
    """, (timestamp, user_id,))
    db.commit()
    db.close()
    return 'UPDATE'

def stats_db_chatters_update(guild_id: int, user_id: int, total_messages_sent: int, first_messages_datetime: datetime.datetime = None, latest_message_datetime: datetime.datetime = None):
    db = sqlite3.connect('stats.db')
    c = db.cursor()
    stats_db_chatters_table_secure(c, guild_id)
    stats_db_chatters_row_secure(c, guild_id, user_id)
    c.execute(f"""
        UPDATE chatters_{guild_id}
        SET total_messages_sent = ?
        WHERE user_id = ?
    """, (total_messages_sent, user_id,))
    if first_messages_datetime:
        c.execute(f"""
            UPDATE emotes_{guild_id}
            SET first_messages_datetime = ?
            WHERE user_id = ?
        """, (first_messages_datetime, user_id,))
    if latest_message_datetime:
        c.execute(f"""
            UPDATE emotes_{guild_id}
            SET latest_message_datetime = ?
            WHERE user_id = ?
        """, (latest_message_datetime, user_id,))
    db.commit()
    db.close()
    return 'UPDATE'


def stats_db_chatters_query_order_by_total_messages_sent(guild_id: int):
    db = sqlite3.connect('stats.db')
    c = db.cursor()
    stats_db_chatters_table_secure(c, guild_id)
    c.execute(f"""
        SELECT * FROM chatters_{guild_id}
        ORDER BY total_messages_sent DESC, first_message_datetime ASC
    """)
    entries = c.fetchall()
    results = []
    for entry in entries:
        results.append({
            "user_id" : entry[0],
            "total_messages_sent" : entry[1],
            "first_message_datetime" : entry[2],
            "latest_message_datetime" : entry[3]
        })
    db.close()
    return results


def stats_chatters_user_object_appendage(interaction: discord.Interaction, query: list):
    for entry in query:
        # entry['user_object'] = interaction.client.get_user(entry['user_id'])
        entry['user_object'] = discord.utils.get(interaction.guild.members, id=entry['user_id'])
    return [entry for entry in query if entry['user_object']]

def stats_chatters_content_generation(query: list, show_per_page: int = 10):
    x, y = len(query), show_per_page
    max_page = int(x//y+(x%y)/(x%y) if x%y!=0 else x//y)

    content_pages = []
    for idx in range(0, max_page): #0:24, 25:49, 50:74, 75:99, ...
        i = idx*y+1
        content = ''
        for entry in query[idx*y:(idx+1)*y]:
            content = content + f"`{i}`　-　{entry['user_object'].mention}　-　{entry['total_messages_sent']}\n"
            i += 1
        content_pages.append(content)
    
    return content_pages
            
def stats_chatters_embed_generation(interaction: discord.Interaction, content_pages: list, page: int = 1):
    embed = discord.Embed(
        color=15158332,
        title=f"Top Chatters",
        description=content_pages[page-1] if content_pages[page-1] else 'None',
        timestamp=datetime.datetime.now()
    )
    embed.set_author(
        name=interaction.guild.name, 
        icon_url=interaction.guild.icon
    )
    return embed



class Stats_Multipage(ui.View):
    def __init__(self, *, timeout: Optional[float] = 180, content_pages: list, embed_generation: 'function'):
        super().__init__(timeout=timeout)
        self.content_pages = content_pages
        self.max_page = len(content_pages)
        self.current_page = 1
        self.embed_generation = embed_generation

    @ui.button(label='< Previous', disabled=True)
    async def previous_callback(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page -= 1
        self.next_callback.disabled = False
        if self.current_page == 1:
            button.disabled = True

        await interaction.message.edit(embed=self.embed_generation(interaction=interaction, content_pages=self.content_pages, page=self.current_page), view=self)
        await interaction.response.defer()

    @ui.button(label='Next >')
    async def next_callback(self, interaction: discord.Interaction, button: ui.Button):
        #0-24, 25-49, 50,74...
        self.current_page += 1
        self.previous_callback.disabled = False
        if self.current_page == self.max_page:
            button.disabled = True

        await interaction.message.edit(embed=self.embed_generation(interaction=interaction, content_pages=self.content_pages, page=self.current_page), view=self)
        await interaction.response.defer()
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)






class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        print(f"Extension loaded: {self.__class__.__name__}")
        return await super().cog_load()
    
    async def cog_unload(self) -> None:
        print(f"Extension unloaded: {self.__class__.__name__}")
        return await super().cog_unload()

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        timestamp = datetime.datetime.now()

        stats_db_chatters_update_increment(message.guild.id, message.author.id, timestamp)

        emote_regex = '(?:<a?)(:\w+:)(?:\d+>)'
        emotes_used = re.findall(emote_regex, message.content)
        
        for emote in emotes_used:
            stats_db_emotes_update_increment(guild_id=message.guild.id, emote_code=emote, timestamp=timestamp)


    stats = app_commands.Group(name='stats', description='Statistics.')

    @stats.command(name='chatters', description='Chatter statistics.')
    async def chatters(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message('This is not a guild bro.')
        
        query = stats_db_chatters_query_order_by_total_messages_sent(guild_id=interaction.guild.id)
        query = stats_chatters_user_object_appendage(interaction, query)

        content_pages = stats_chatters_content_generation(query)
        embed = stats_chatters_embed_generation(interaction, content_pages)
        view = Stats_Multipage(content_pages=content_pages, embed_generation=stats_chatters_embed_generation)
        view.next_callback.disabled = True if len(content_pages)==1 else False

        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
    
    @stats.command(name='emotes', description='Emotes statistics.')
    async def emotes(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message('This is not a guild bro.')
        
        query = stats_db_emotes_query_order_by_usage(guild_id=interaction.guild.id)
        emojis = {e.name:str(e) for e in interaction.client.emojis}
        query = stats_emotes_discord_code_appendage(query, emojis)

        content_pages = stats_emotes_content_generation(query)
        embed = stats_emotes_embed_generation(interaction, content_pages)
        view = Stats_Multipage(content_pages=content_pages, embed_generation=stats_emotes_embed_generation)
        view.next_callback.disabled = True if len(content_pages)==1 else False

        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()


    @stats.command(name='scan', description='Scan server history to update the stats.')
    async def scan(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message('This is not a guild bro.')
        
        await interaction.response.defer()

        messages = []
        for channel in interaction.guild.text_channels:
            messages += [message async for message in channel.history(limit=None)]
        print(len(messages))
        
        total_messages_sent_temp = {}
        emotes_usage_temp = {}
        emote_regex = '(?:<a?)(:\w+:)(?:\d+>)'
        for message in messages:
            total_messages_sent_temp[message.author.id] = total_messages_sent_temp[message.author.id] + 1 if message.author.id in total_messages_sent_temp else 1

            emotes_used = re.findall(emote_regex, message.content)
            for emote in emotes_used:
                emotes_usage_temp[emote] = emotes_usage_temp[emote] + 1 if emote in emotes_usage_temp else 1
        
        for user_id in total_messages_sent_temp:
            print(user_id, total_messages_sent_temp[user_id])
            update = stats_db_chatters_update(guild_id=interaction.guild.id, user_id=user_id, total_messages_sent=total_messages_sent_temp[user_id])
            print(update)

        for emote in emotes_usage_temp:
            print(emote, emotes_usage_temp[emote])
            update = stats_db_emotes_update(guild_id=interaction.guild.id, emote_code=emote, usage=emotes_usage_temp[emote])
            print(update)
        
        await interaction.followup.send('Scanned.')




async def setup(bot):
    await bot.add_cog(Stats(bot))