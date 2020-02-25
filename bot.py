#Chatty Bot
#Created for the r/PokemonMaxRaids discord server
#Authored by Ymir | Prince_of_Galar and Eldaste

#setup
import discord
import asyncio
import os
import re
import postgres
from discord.utils import get

# Establish settings and IO helpers
MODROLE = "Mods"
COMMANDCHNNUM = int(os.environ.get('COMMANDCHN'))

def loadMentions():
    tmpm = {}
    with open('./data/mentioninfo.txt') as f:
        for line in f:
            tt = line.split('|')
            key, rest = tt[0], tt[1:]
            tmpm[key] = rest
    return tmpm

warninglist = []
mention_dict = loadMentions()
db = postgres.Postgres(url = os.environ.get('DATABASE_URL'))
db.run("CREATE TABLE IF NOT EXISTS forbidden (words text)")

client = discord.Client()
commandChn = None

#Helper function to help create the warnings
def composeWarning(values):
    temp = '|'.join(map(str, values))
    temp = r'\W(' + temp + r')\W\Z'
    return re.compile(temp, re.I)

#Composed awarning (a regex object)
composedwarning = composeWarning(warninglist)

#Monitor all messages for danger words and report them to the mods
#Also reply to messages with certian mentions in them
@client.event
async def on_message(msg):
    # Handle commands
    global warninglist, composedwarning
                
    if not msg.author.bot and msg.channel.id == COMMANDCHNNUM:
        if get(msg.author.roles, name = MODROLE):
            #print('Command Recieved')
            splitmes = msg.content.split()
            
            if len(splitmes) == 0:
                return
            
            if splitmes[0] == ';get':
                await commandChn.send(', '.join(map(lambda x: '`' + x + '`', warninglist)))
            elif splitmes[0] == ';set':
                if len(splitmes) == 1:
                    await commandChn.send('What word or regular expression would you like to be notified of?')
                    return
                warninglist.append(splitmes[1])
                db.run("INSERT INTO forbidden VALUES (%(new)s)", new = splitmes[1])
                composedwarning = composeWarning(warninglist)
                await commandChn.send('Word added.')
            elif splitmes[0] == ';rm':
                if len(splitmes) == 1:
                    await commandChn.send('What word or regular expression would you like to not be notified of?')
                    return
                warninglist.remove(splitmes[1])
                db.run("DELETE FROM forbidden WHERE words=(%(old)s)", old = splitmes[1])
                composedwarning = composeWarning(warninglist)
                await commandChn.send('Word removed.')
            elif splitmes[0] == ';help':
                await commandChn.send(';get - What words are being watched for.\n;set - Add a word.\n;rm - Remove a word.')
            #else:
            #    await commandChn.send('What do I do with this?')
        return
        
    # If from a bot or the mods, ignore
    if msg.author.bot or get(msg.author.roles, name = MODROLE):
        return

    # Analyze the message for warning words, notify mods if any appear
    dangerwords = filter(composedwarning.match, msg.content.split())

    cdw = ', '.join(map(str, dangerwords))
    if cdw != '':
        warnmess = discord.Embed()
        warnmess.title = 'Warning Report'
        warnmess.add_field(name = 'User', value = msg.author)
        warnmess.add_field(name = 'Words Used', value = cdw)
        warnmess.add_field(name = 'Message Link', value = msg.jump_url)
        await commandChn.send(embed = warnmess)

    # Check mentions of a message and send messages when needed
    for mention in msg.role_mentions:
        val = str(mention.id)
        if val in mention_dict:
            await msg.channel.send('\n'.join(map(str, mention_dict[val])))

#If a user with the Max Host role adds a :pushpin: (📌) reaction to a message, the message will be pinned
@client.event
async def on_raw_reaction_add(payload):
    guild = await client.fetch_guild(guild_id = payload.guild_id)
    member = await guild.fetch_member(member_id = payload.user_id)
    if payload.emoji.name == "📌" and get(member.roles, name = "Max Host"):
        channel = client.get_channel(id = payload.channel_id)
        message = await channel.fetch_message(id = payload.message_id)
        await message.pin()

#If a user with the Max Host role removes a :pushpin: (📌) reaction from the message, the message will be unpinned
@client.event
async def on_raw_reaction_remove(payload):
    guild = await client.fetch_guild(guild_id = payload.guild_id)
    member = await guild.fetch_member(member_id = payload.user_id)
    if payload.emoji.name == "📌" and get(member.roles, name = "Max Host"):
        channel = client.get_channel(id = payload.channel_id)
        message = await channel.fetch_message(id = payload.message_id)
        await message.unpin()

#When bot is ready, open the command channel
@client.event
async def on_ready():
    global commandChn, warninglist, composedwarning
    commandChn = client.get_channel(COMMANDCHNNUM)
    warninglist = db.all('SELECT words FROM forbidden')
    composedwarning = composeWarning(warninglist)
    print('Logged in as ' + client.user.name)

#runs the app
if __name__ == '__main__':
    client.run(os.environ.get('TOKEN'))
