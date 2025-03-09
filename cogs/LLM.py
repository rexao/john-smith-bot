import datetime
import json
import random
import re
import traceback
from typing import List


import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI



# Tools
class LLM_tools():

    def get_now(self) -> str:
        print("Tool calling: get_now")
        return datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=9)))

    def get_socials(self, user: str) -> str:
        print(f"Tool calling: get_socials({user})")
        re_match = re.search(r"<\s*@\s*(\w+)\s*>|@\s*(\w+)", user)
        user = user.strip() if not re_match else re_match.group(1) or re_match.group(2)
        with open("data/llm_socials.json", "r", encoding="utf-8") as f:
            data: dict = json.load(f)
            target_data: dict = data.get(user, {})
        return '\n'.join([url for url in target_data.values() if url]) if target_data else "Given user has no socials found."

llm_tools = LLM_tools()



# OpenAI Python library
llm_client = AsyncOpenAI(
    base_url="http://rexao.ddns.net:11434/v1",
    api_key="ollama",
)
default_llm = "llama3.2:latest"

def llm_respond(message: str):
   completion = llm_client.chat.completions.create(
        model=default_llm,
        messages=[
            {"role": "system", "content": scenario},
            {"role": "user", "content": message}
        ]
    )
   completion = completion.choices[0].message.content
   # DeepSeek parsing
   completion = ds_parse(message)
   return completion

def ds_parse(response: str):
    return re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()


# Testing purpose
def main():
    print(llm_respond(sample_message))

if __name__ == "__main__":
    main()


# Discord.py
async def setup(bot):
    await bot.add_cog(LLM(bot))

class LLM(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.llm_model = default_llm
        self.llm_temperature = 100
        self.llm_tools = [
            {
                "type": "function",
                "funciton": {
                    "name": "get_now",
                    "description": "Retrieve current date and time.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            },
            {
                "type": "function",
                "funciton": {
                    "name": "get_socials",
                    "description": "Retrieve a user's socials.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user": {
                                "type": "string",
                                "description": "The user to retrieve socials of."
                            }
                        },
                        "required": ["user"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        ]
        self.context_scope = 20
        self.random_response = 10
        

    async def cog_load(self) -> None:
        print(f"Extension loaded: {self.__class__.__name__}")
        return await super().cog_load()
    
    async def cog_unload(self) -> None:
        print(f"Extension unloaded: {self.__class__.__name__}")
        return await super().cog_unload()
    
    llm = app_commands.Group(name='llm', description='Tweak John\'s AI.')
    
    @llm.command(name='settings', description='See or adjust the settings.')
    @app_commands.describe(
        model="Change what model John Smith runs on.",
        temperature="Change sampling temperature. (0-200)",
        context_scope="Change the maximum number of recent messages John Smith can see. Affects performance.",
        random_response="Change how frequently John Smith responds unmentioned. (0-100)"
    )
    async def settings(
        self, interaction: discord.Interaction,
        model: str = None,
        temperature: int = None,
        context_scope: int = None,
        random_response: int = None
    ):
        message_content = []
        if not (model or temperature or context_scope or random_response):
            return await interaction.response.send_message(f"""
Currently running on `{self.llm_model}`.
Temperature set to `{self.llm_temperature}`.
Context scope set to `{self.context_scope}`.
Random response rate set to `{self.random_response}`.
""")
        if model:
            self.llm_model = model
            message_content.append(f"Switched to `{self.llm_model}`.")
        if temperature:
            self.llm_temperature = temperature if temperature >= 0 else 0
            self.llm_temperature = temperature if temperature <= 200 else 200
            message_content.append(f"Temperature set to `{self.llm_temperature}`.")
        if context_scope:
            self.context_scope = context_scope if context_scope >= 0 else 0
            message_content.append(f"Context scope set to `{self.context_scope}`.")
        if random_response:
            self.random_response = random_response if random_response >= 0 else 0
            self.random_response = random_response if random_response <= 100 else 100
            message_content.append(f"Random response rate set to `{self.random_response}`.")
        return await interaction.response.send_message("\n".join(message_content))

    @settings.autocomplete(name='model')
    async def model_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        available_models = (await llm_client.models.list()).data
        choices = sorted(
            [app_commands.Choice(
                name=model.id,
                value=model.id
            ) for model in available_models],
            key=lambda choice: choice.name
        )
        return [choice for choice in choices if current.lower() in choice.name.lower()][:25]
    
    # Trace a reply thread above a discord.Message and return a list of discord.Message
    async def _trace_thread(self, message: discord.Message):
        thread = [message]
        while True:
            if message.reference:
                reference_message = message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
                thread.insert(0, reference_message)
                message = reference_message
            else:
                break
        return thread

    # Format a discord.Message into a str for prompt
    def _format_content(self, message: discord.Message):
        content = message.content
        for member in message.mentions:
            content = re.sub(member.mention, f"<@{member.name}>", content)
        for channel in message.guild.channels:
            content = re.sub(channel.mention, f"<#{channel.name}>", content)
        for role in message.guild.roles:
            content = re.sub(role.mention, f"<#{role.name}>", content)
        for emoji in self.bot.emojis:
            if emoji.animated:
                content = re.sub(f"<a:{emoji.name}:{emoji.id}>", f":{emoji.name}:", content)
            else:
                content = re.sub(f"<{emoji.name}:{emoji.id}>", f":{emoji.name}:", content)
        for embed in message.embeds:
            embed_content = "\n\n".join([str(c) for c in [
                embed.provider.name if embed.provider else "",
                embed.author.name if embed.author else "",
                embed.title,
                embed.description,
                "\n\n".join([f"**{field.name}**\n{field.value}" for field in embed.fields]),
                embed.footer.text if embed.footer else "",
                embed.timestamp.strftime("%Y/%m/%d %H:%M:%S") if embed.timestamp else ""
            ] if c])
            content = f"{content}\n\n{embed_content}"
        return content

    # Compile a prompt with a list of discord.Message
    async def _compile_prompt(self, context: List[discord.Message]):
        prompt = [
            {
                "role": "system",
                "content": scenario(option=1, now=datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=9))), guild=context[-1].guild)
            }
        ]    
        for message in context:
            if message.is_system():
                continue
            if message.reference:
                reference_message = message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
                prompt.append({
                    "role": "user" if message.author != self.bot.user else "assistant",
                    "content": f"> <@{reference_message.author.name}>: {self._format_content(reference_message)}\n\n<@{message.author.name}>: {self._format_content(message)}"
                })
            else:
                prompt.append({
                    "role": "user" if message.author != self.bot.user else "assistant",
                    "content": f"<@{message.author.name}>: {self._format_content(message)}" 
                })
        return prompt
    
    

    async def _chat_completion(self, messages: List[dict]):
        completion = await llm_client.chat.completions.create(
            messages=messages,
            model=self.llm_model,
            temperature=(self.llm_temperature/100)
            # tools=self.llm_tools
        )
        

            
        message = completion.choices[0].message.content.strip()
        return message

    # This returns the async send/reply function after formatting
    def _reply_formatted(self, target_message: discord.Message, content: str, reply: bool = False):
        content = ds_parse(content)
        # content = re.sub(r"^<?@John Smith>?:\s*\n?", "", content, flags=re.IGNORECASE)
        content = content.split("<@John Smith>: ")[-1]
        for member in target_message.guild.members:
            content = re.sub(f"<@{member.name}>", member.mention, content, flags=re.IGNORECASE)
            content = re.sub(f"<@{member.display_name}>", member.mention, content, flags=re.IGNORECASE)
        for member in sorted(target_message.guild.members, key=lambda member: member.name, reverse=True):
            content = re.sub(f"@{member.name}", member.mention, content, flags=re.IGNORECASE)
            content = re.sub(f"@{member.display_name}", member.mention, content, flags=re.IGNORECASE)
        for channel in target_message.guild.channels:
            content = re.sub(f"<#{channel.name}>", channel.mention, content, flags=re.IGNORECASE)
            # content = re.sub(f"#{channel.name}", channel.mention, content, flags=re.IGNORECASE)
        for role in target_message.guild.roles:
            content = re.sub(f"<@{role.name}>", role.mention, content, flags=re.IGNORECASE)
            # content = re.sub(f"@{role.name}", role.mention, content, flags=re.IGNORECASE)
        for emoji in [emoji for emoji in self.bot.emojis if emoji.guild.name.startswith("Labo ")]:
            content = re.sub(f":{emoji.name}:", str(emoji), content, flags=re.IGNORECASE)
        if len(content) >= 2000:
            content = f"{content[:1997]}..."
            embed = overlength_embed
        else:
            embed = None
        if reply:
            return target_message.reply(content=content, embed=embed)
        else:
            return target_message.channel.send(content=content, embed=embed)

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_message(self, message: discord.Message):        
        if message.author == self.bot.user:
            return
        
        reference_message = None if not message.reference else message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
        replied_to = None if not reference_message else reference_message.author == self.bot.user
        mentioned = (self.bot.user in message.mentions) or (message.guild.self_role in message.role_mentions) or message.mention_everyone
        
        try:
            context = [cached for cached in self.bot.cached_messages if cached.channel.id == message.channel.id][-self.context_scope:]
            if message.reference:
                context += await self._trace_thread(message=message)
                context = sorted(
                    list(set(context)),
                    key=lambda message: message.created_at
                )
            if (replied_to or mentioned) or (random.random() < (self.random_response/100)):
                print("LLM working...")
                async with message.channel.typing():
                    messages = await self._compile_prompt(context=context)
                    print(messages)
                    print(len(messages))
                    response = await self._chat_completion(messages=messages)
                    print(response)
                    await self._reply_formatted(target_message=message, content=response, reply=(replied_to or mentioned))
        except Exception as e:
            content=f"```{''.join(traceback.format_exception(e))}```"
            print(content)
            await message.channel.send(content)