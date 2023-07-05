import os
import openai
import yt_dlp as youtube_dl
import discord
import asyncio
import json
import nest_asyncio
import threading

from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks

openai.api_key = "" ##API KEY HERE

susBot = None
singularity = None
whereAmI = None
music_queue = {}

nest_asyncio.apply()

class Open_ai_chat(commands.Cog, name="open_ai_chat"):

    def __init__(self,bot):
        self.bot=bot

    @commands.Cog.listener()
    async def on_message(self,message):
        global whereAmI
        whereAmI=message
        if(message.author.bot or message.content.startswith('!')):
            return
        if message.author.id != 608738013723361419:
            return
        messages = [msg async for msg in message.channel.history(limit=5)]
        formattedMsg = formatting_messages(messages)
        try:
            await message.channel.send(await get_response(formattedMsg))
        except Exception as e:
            raise e

    @commands.command(
            name="change_character",
            description="Changes the way the chatBot acts."
    )
    async def changeCharacter(self,ctx,*,arg):
        global singularity
        if arg=="defult":
            singularity=None
        elif arg=="devMode":
            with open('cogs/chat-characters/devModeGPT.txt','r') as f:
                lines = f.readlines()
                singularity = ''.join(lines)
        else:
            await ctx.send("Character does not exist...yet, but we have:\ndefult\ndevMode")
            return
        await ctx.send("Character changed to "+arg)

    @commands.command(name='play', description='Tells the bot to play music but only with url')
    async def play(self,ctx,url):
        if not ctx.author.voice:
            try:
                await ctx.channel.send("{} is not connected to a voice channel".format(ctx.message.author.name))
            except:
                await ctx.channel.send("{} is not connected to a voice channel".format(ctx.author.name))
            return
        else:
            channel = ctx.author.voice.channel

        try:
            await channel.connect()
        except:
            pass

        music_info=get_music_info(url)
        music_name=music_info['fulltitle']

        try : ####
            server = ctx.guild
            voice_channel = server.voice_client
            try:
                filename = await YTDLSource.from_url(url)
            except:
                ctx.channel.send('Song not found!')
            new_filename = f'{ctx.guild.id}.webm'
            os.rename(filename,new_filename)
            voice_channel.play(discord.FFmpegPCMAudio(executable="cogs/ffmpeg-1", source=new_filename), after = lambda x=None: check_queue(ctx, ctx.guild.id))
            await ctx.channel.send('**Now playing:** {}'.format(music_name))
        except Exception as e:
            if str(e) == "Already playing audio.":
                guild_id = ctx.guild.id
                filename = await YTDLSource.from_url(url)
                new_filename = f'{ctx.guild.id}.webm'
                os.rename(filename,new_filename)
                source = discord.FFmpegPCMAudio(executable="cogs/ffmpeg-1", source=new_filename)
                if guild_id in music_queue:
                    music_queue[guild_id].append(source)
                else:
                    music_queue[guild_id] = [source]
                await ctx.channel.send('**Queued:** {}'.format(music_name))
                print(len(music_queue[guild_id])) ##
            else:
                raise e

    @commands.command(name='skip', description='Skips to next song')
    async def skip(self,ctx):
        global music_queue
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            voice_client.stop()
        if len(music_queue)>0:
            source = music_queue[ctx.message.guild.id].pop(0)
            voice_client.play((source), after = lambda x=None: check_queue(ctx,ctx.message.guild.id))
        else:
            return
        

    @commands.command(name='leave', description='Bot stops playing music and leaves the voice channel')
    async def leave(self,ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_connected():
            await voice_client.disconnect()
        else:
            await ctx.send("The bot is not connected to a voice channel.")

    @commands.command(name='resume', description='Resumes the song')
    async def resume(self,ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_paused():
            await voice_client.resume()
        else:
            await ctx.send("The bot was not playing anything before this. Use play_song command")

    @commands.command(name='queue', description='queues the song')
    async def queue(self,ctx,url):
        global music_queue
        if not ctx.author.voice:
            await ctx.channel.send("{} is not connected to a voice channel".format(ctx.message.author.name))
            return
        guild_id = ctx.message.guild.id
        filename = await YTDLSource.from_url(url)
        song_info = get_music_info(url)
        song_name = song_info['fulltitle']
        new_filename = f'{ctx.message.guild.id}.webm'
        os.rename(filename,new_filename)
        source = discord.FFmpegPCMAudio(executable="cogs/ffmpeg-1", source=new_filename)
        if guild_id in music_queue:
            music_queue[guild_id].append(source)
        else:
            music_queue[guild_id] = [source]
        await ctx.channel.send('**Queued:** {}'.format(song_name))


    
def formatting_messages(messages):
    global singularity
    if singularity is None:
        with open('cogs/chat-characters/defult.txt','r') as f:
                lines = f.readlines()
                singularity = ''.join(lines)
    formattedMsg=[{"role":"system","content":singularity}]
    messages.reverse()
    for x in messages:
        if(not x.author.bot):
            formattedMsg.append({"role":"user","content":str(x.content)})
        else:
            formattedMsg.append({"role":"assistant","content":str(x.content)})
    return formattedMsg

async def get_response(input):
    functions = [
        {
            "name": "get_music",
            "description": "gets information on music with url and plays the music on the requester's voice channel",
            "parameters": 
            {
                "type": "object",
                "properties": 
                {
                    "input": 
                    {
                        "type": "string",
                        "description": """The url for the song from youtube. e.g. https://www.youtube.com/watch?v=ouLndhBRL4w 
                        or the name of the song. e.g Hello find Hello by Adele. A song might already be playing, so people might also
                        ask you to play something next e.g. Yo Imposter play Idol by Yoasobi next. In these cases use the same function.""",
                    },
                },
                "required": ["url"],
            },
        }
    ]
    response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=input,
            functions=functions,
            function_call="auto",
    )
    response_message = response['choices'][0]['message']

    if response_message.get("function_call"):
        available_functions = {
            "get_music": get_music,
        } 
        function_name = response_message["function_call"]["name"]
        fuction_to_call = available_functions[function_name]
        function_args = json.loads(response_message["function_call"]["arguments"])
        function_response = fuction_to_call(
            input=function_args.get("input"),
        )

        input.append(response_message)  
        input.append(
            {
                "role": "function",
                "name": function_name,
                "content": function_response,
            }
        )
        second_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=input,
        ) 
        return str(second_response['choices'][0]['message']['content'])
    return response_message['content']

#####   ^Open Ai^   #####

#####   Open Ai Methods  #####
def get_music(input): ##Get Music Command for openAI
    global whereAmI
    global susBot
    videoInf=get_music_info(input)
    finalInfo = {a:b for a,b in videoInf.items() if not(type(b) is list or type(b) is dict or len(str(b)) > 150)}
    try:
        asyncio.get_event_loop().run_until_complete(Open_ai_chat.play(susBot,whereAmI,videoInf['webpage_url']))
    except Exception as e:
        raise e
    return json.dumps(ytdl.sanitize_info(finalInfo))

#####   Other Methods   #####
#####   Music   ##### 
def get_music_info(name_of_song):   ##returns dict of info about music. e.g return['webpage_url']
    videoInf=ytdl.extract_info(f"ytsearch:{name_of_song}",download=False)
    try:
        videoInf=videoInf['entries'][0]
    except:
        videoInf=videoInf
    return videoInf

def check_queue(ctx,id): 
    global music_queue
    if music_queue[id] != []:
        voice = ctx.guild.voice_client
        source = music_queue[id].pop(0)
        player = voice.play(source)

#####   Youtube_dl ect  #####
#####   YTDL OPTIONS DO NOT TOUCH   #####

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'forceurl': True,
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename

async def setup(bot):
    global susBot
    susBot = bot
    await bot.add_cog(Open_ai_chat(bot))
