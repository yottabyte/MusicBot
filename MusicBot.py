import asyncio
import discord
import re
import datetime
import youtube_dl
import os
import traceback

if not discord.opus.is_loaded():
    discord.opus.load_opus('libopus-0.dll')

try:
    with open('blacklist.txt') as f:
        blacklist = f.readlines()
    for i, item in enumerate(blacklist):
        whitelist[i] = item.rstrip()
    with open('whitelist.txt') as f:
        whitelist = f.readlines()
    for i, item in enumerate(whitelist):
        whitelist[i] = item.rstrip()
    with open('options.txt') as f:
        options = f.readlines()
    for i, item in enumerate(options):
        options[i] = item.rstrip()
except:
    print('one of the text files was deleted, reinstall')

savedir = "playlist"
if not os.path.exists(savedir):
    os.makedirs(savedir)
    
MAX_VIDEO_LENGTH = 15*60
directive = 'none'
isPlaying = False
firstTime = True

ownerID = options[4]
skipsRequired = int(options[5])
skipCount = 0
skipperlist = []
timeSinceLast = 0

playlist = []
currentlyPlaying = ''

helpmessage = '`!play [youtube link]` will allow me to play a new song or add it to the queue.\n`!play playlist` will print out all links to youtube videos currently in the queue!\n`!play skip` will make it skip to the next song after 4 people vote to skip the current one!'

channel = 0

client = discord.Client()

@client.async_event
def on_ready():
    print('Connected!')
    print('Username: ' + client.user.name)
    print('ID: ' + client.user.id)
    print('--Server List--')
    for server in client.servers:
        print(server.name)
        
@client.async_event
def on_message(message):
    global directive
    global ownerID
    global firstTime
    global skipCount
    global channel
    global skipperlist
    deleteMyMsg = False

    if message.author == client.user:
        return

    if message.channel.is_private:
        yield from client.send_message(message.channel, 'You cannot use this bot in private messages.')

    if '!whatismyuserid' in message.content.lower():
        print(message.author.id)

    if '!whitelist' in message.content.lower() and message.author.id == ownerID:
        msg = message.content
        substrStart = msg.find('!whitelist') + 11
        msg = msg[substrStart: ]
        msg.strip()
        msg = re.sub('<|@|>', '', msg)
        f = open('whitelist.txt', 'a')
        f.write(msg + "\r")
        f.close()
        whitelist.append(msg)

    elif '!blacklist' in message.content.lower() and message.author.id == ownerID:
        msg = message.content
        substrStart = msg.find('!blacklist') + 11
        msg = msg[substrStart: ]
        msg.strip()
        msg = re.sub('<|@|>', '', msg)
        f = open('blacklist.txt', 'a')
        f.write(msg + "\r")
        f.close()
        blacklist.append(msg)

    elif '!playlist' in message.content.lower():
        print('they want playlist')
        if playlist :
            endmsg = getPlaylist()
            yield from client.send_message(message.channel,endmsg)
        else:
            yield from client.send_message(message.channel,'tits no playlist bitch')

    elif '!skip' in message.content.lower():
        if message.author.id == ownerID:
            yield from client.send_message(message.channel,'\u26A0 `'+message.author.name+'` used his malicious fascist powers to skip song.')
            skipperlist = []
            skipCount = 0
            directive = 'skip'
        elif message.author.id not in skipperlist:
            skipperlist.append(message.author.id)
            skipCount+=1
            yield from client.send_message(message.channel,'\u23E9 `'+message.author.name+'` wants to skip song `'+str(skipCount)+'/'+str(skipsRequired)+'`')
        else:
            print('already voted to skip')
        if skipCount >= skipsRequired:
            skipperlist = []
            skipCount = 0
            directive = 'skip'

    elif '!play' in message.content.lower():

        # Clean up the message
        msg = message.content
        msg2 = msg
        substrStart = msg.find('!play') + 6
        msg = msg[substrStart: ]
        msg.strip()
        addSong = False

        # No reason to do anything if they didn't type anything after "play"
        if len(msg.lower()) < 2:
            yield from client.send_message(message.channel, '\u26A0 ' + message.author.name + ' is a fucking moron')
            return

        # Don't allow blacklisted users to use this command.
        if message.author.id in blacklist :
            print('no, blacklisted')

        # If the whitelist if active, #checkyourprivilege
        elif (options[2]=='1' and not is_long_member(message.author.joined_at)) and message.author.id not in whitelist:
            print('no, not whitelisted and new')

        # This is still here for some reason. 
        elif msg.lower() == 'help':
            hotsmessage = yield from client.send_message(message.channel,helpmessage)
            deleteMyMsg = True

        # Allow owner to move the bot to his channel
        elif msg.lower() == 'move' and message.author.id == ownerID:
            yield from client.voice.disconnect()
            vce = yield from client.join_voice_channel(message.author.voice_channel)

        # Allow owner to tell the bot to leave voice
        elif msg.lower() == 'leave' and message.author.id == ownerID:
            yield from client.voice.disconnect()
            firstTime = True
            directive = 'none'

        # Default behaviour once play command is sent.
        else:
            channel = message.channel
            if firstTime is True:
                vce = yield from client.join_voice_channel(message.author.voice_channel)
            yield from client.send_message(message.channel, '\uD83C\uDFB6 `' + message.author.name + '` queued `' + msg + '`')
            addSong = True

        try:
            yield from client.delete_message(message)
        except:
            print('Couldn\'t delete message for some reason')

        # Adding song is handled separately after command parsing because of how long it takes the program to search youtube
        if addSong:
            error = addSongToPlaylist(msg, message.author.name)
            print('Error: ' + error)
            if error == 'length':
                yield from client.send_message(message.channel, '\u26A0 `' + message.author.name + '` tried to queue a song longer than 15 minutes like the idiot he is.')
            elif error == 'dunno':
                yield from client.send_message(message.channel, '\u26A0 `' + message.author.name + '` tried to queue a song with a broken link. Nice.')

    # Wait for a bit before deleting my message
    if deleteMyMsg is True:
        deleteMyMsg = False
        yield from asyncio.sleep(4)
        yield from client.delete_message(hotsmessage)

def is_long_member(dateJoined):
    convDT = dateJoined.date()
    today = datetime.date.today()
    optDays = options[1]
    margin = datetime.timedelta(days = int(options[1]))
    return today - margin > convDT

def addSongToPlaylist(unfixedsongURL, user):
    global firstTime

    # Clean up youtube links from junk
    if 'youtube' in unfixedsongURL:
        if '&' in unfixedsongURL:
            substrStart = unfixedsongURL.find('&')
            songURL = unfixedsongURL[ :substrStart]
            songURL.strip()
        else:
            songURL = unfixedsongURL
    else:
        songURL = unfixedsongURL

    options = {
            'format': 'bestaudio/best',
            'noplaylist' : True,
            'nocheckcertificate' : True,
        'default_search': 'auto',
        'simulate': True}
    ydl = youtube_dl.YoutubeDL(options)

    try:
        info = ydl.extract_info(songURL, download=False)
        f = open('myfile','w')
        try:
            firstTime = False
            title = info['title']
            if info['duration'] > MAX_VIDEO_LENGTH: 
                return 'length'
            playlist.append([songURL, title, user])
            print('Adding song ' + title)
        except KeyError:
            print('youtube_dl gave me a list. probably a search then.')
            return addSongToPlaylist(info['entries'][0]['webpage_url'], user)

    except Exception as e:
        print("Can't access song! %s\n" % traceback.format_exc())
        return 'dunno'
    
    return 'none'

def getPlaylist():
    endmsg = ''
    count = 0
    for songs in playlist:
        count+=1
        endmsg = endmsg + str(count) + '. `' + songs[1] + '` requested by `' + songs[2] + '` \n'
    return endmsg

def make_savepath(title, savedir=savedir):
    return os.path.join(savedir, "%s.mp3" % (title))

def download_song(song):
    options = {
        'format': 'bestaudio/best',
        'extractaudio' : True,
        'audioformat' : "mp3",
        'outtmpl': '%(id)s',
        'noplaylist' : True,
            'nocheckcertificate' : True}
    ydl = youtube_dl.YoutubeDL(options)

    try:
        title = re.sub(r'\W+', '', song[1])
        savepath = make_savepath(title)
    except Exception as e:
        print("Can't access song! %s\n" % traceback.format_exc())
        return 'invalid'

    try:
        os.stat(savepath)
        return savepath
    except OSError:
        try:
            result = ydl.extract_info(song[0], download=True)
            os.rename(result['id'], savepath)
            return savepath
        except Exception as e:
            print ("Can't download audio! %s\n" % traceback.format_exc())
            return 'invalid'

@asyncio.coroutine
def playlist_update():
    global isPlaying
    global timeSinceLast
    global directive
    global firstTime
    global channel
    yield from client.wait_until_ready()
    count = 0
    time = 0
    while count!= -1:
        print('Ding! Directive: ' + directive)
        if isPlaying is False and firstTime is False:
            if playlist:
                vce = client.voice
                nextSong = playlist[0]
                try:
                    path = download_song(nextSong)
                    print('Downloaded, path is ' + path)
                    if path != 'invalid':
                        player = vce.create_ffmpeg_player(path, options='''-filter:a "volume={}"'''.format(0.2))
                        player.start()
                        isPlaying = True
                        timeSinceLast = 0

                        yield from client.send_message(channel, '\u25B6 Now: `' + nextSong[1] + '` requested by `' + nextSong[2] + '`')
                        if len(playlist) > 1: 
                            yield from client.send_message(channel, '\u23E9 Next: `' + playlist[1][1] + '` requested by `' + playlist[1][2] + '`')

                        while nextSong in playlist: playlist.remove(nextSong)
                        directive = 'sleep'
                    else:
                        while nextSong in playlist: playlist.remove(nextSong)
                except:
                    while nextSong in playlist: playlist.remove(nextSong)
            else:
                print("Playlist empty, waiting... " + str(timeSinceLast))
                if timeSinceLast > 180:
                    yield from client.voice.disconnect()
                    firstTime = True
                    directive = 'none'
                    timeSinceLast = 0
                else:
                    timeSinceLast += 1
                    yield from asyncio.sleep(1)
                    directive = 'sleep'
        if directive == 'sleep' or directive == 'skip':
            try:
                print('sleep/skip')
                cnt = 0
                while directive!='skip' and player.is_playing():
                    cnt+=1
                    yield from asyncio.sleep(1)
                player.stop()
                isPlaying = False
                directive = "none"
            except UnboundLocalError:
                directive = "none"
        else:
            yield from asyncio.sleep(1)

loop = asyncio.get_event_loop()
try:
    loop.create_task(playlist_update())
    loop.run_until_complete(client.login(options[0], options[1]))
    loop.run_until_complete(client.connect())
except Exception:
    loop.run_until_complete(client.close())
finally:
    loop.close()