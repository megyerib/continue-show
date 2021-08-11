import os, sys, glob, re, configparser, json, urllib.parse, subprocess, time

# Arguments
if len(sys.argv) < 3:
    print("Missing argument!")
    print(f"Usage: python {os.path.basename(__file__)} [vlc_path] [vlc_history_file_path]")
    exit()

vlc_path = sys.argv[1]
vlc_history_path = sys.argv[2]

# Constants
valid_file_types = {'mp4', 'mkv', 'avi'}
json_history_name = 'recently_played.json'

"""
return: The list of videos in the current directory and its subdirectories
"""
def list_videos():
    files = glob.glob("**/*", recursive = True) # List all files, filter later
    
    re_object = re.compile(f".+\.({'|'.join(valid_file_types)})$") #File type filter
    videos = list(filter(re_object.match, files))
    
    ret = []
    
    for video in videos:
        ret.append(video.replace('\\', '/')) # Replace Windows path backslashes

    return ret

"""
path:   VLC ini file path

return: VLC history list [{path (abs), time}]; newest to oldest
"""
def list_vlc_history(path):
    config = configparser.RawConfigParser() # https://stackoverflow.com/a/2538141/2721340
    try:
        config.read(path)
    except:
        print(f"VLC history file '{path}' does not exist.")
        return []
    
    try:
        # Remove trailing commas
        if config['RecentsMRL']['list'][-1] == ',':
            config['RecentsMRL']['list'] = config['RecentsMRL']['list'][:-1]
            config['RecentsMRL']['times'] = config['RecentsMRL']['times'][:-1]
        
        # Split
        list = [path.replace('file:///', '') for path in config['RecentsMRL']['list'].split(', ')]
        times = [int(int(time)/1000) for time in config['RecentsMRL']['times'].split(', ')]
    except:
        print("History cannot be read from VLC history file.")
        return []
        
    ret = []
    
    for i in range(0, len(list)):
        ret.append({'path': urllib.parse.unquote(list[i]), 'time': times[i]}) # eg. %20 -> ' '

    return ret

"""
return: recently played video which is located in the current directory from VLC history file
        {path, time} if there is such video in the history
        None if there is no such file in the history
"""
def get_recently_played_from_vlc_history():
    cwd = os.getcwd().replace('\\', '/') # For Windows paths

    p = re.compile(f"^{cwd}/.+")

    history = list_vlc_history(vlc_history_path)

    for entry in history:
        if p.match(entry['path']):
            return entry
    
    return None

"""
return: recently played video from own history file {path (absolute), time}
        None if history file does not exist
"""
def get_recently_played_from_json(path):
    try:
        with open(path) as json_file:
            entry = json.load(json_file)
            cwd = os.getcwd().replace('\\', '/')
            entry['path'] = f"{cwd}/{entry['path']}"
            return entry
    except:
        print("JSON history file does not exist")
        
    return None

"""
return: recently played video from VLC history file if exists
        recently played video from own history file if file exists
        None if both lookups are unsuccessful
"""
def get_recently_played():
    recently_played = get_recently_played_from_vlc_history()
    
    if None == recently_played:
        recently_played = get_recently_played_from_json(json_history_name)
    
    return recently_played

"""
return: recently played video if it wasn't finished
        next video if recently played video was finished
"""
def get_video_to_play():
    entry = get_recently_played()
    videos = list_videos()
    
    if None != entry:
        if 0 != entry['time']:
            video_to_play = entry
        else:
            videos = list_videos()
            cwd = os.getcwd().replace('\\', '/')
            
            index = 0
            
            for i in range(0, len(videos)):
                if f"{cwd}/{videos[i]}" == entry['path']:
                    index = i
                    break
            
            video_to_play = {'path': videos[(index + 1) % len(videos)], 'time': 0}
    elif len(videos) != 0:
        video_to_play = {'path': videos[0], 'time': 0}
    else:
        return None
    
    return video_to_play

"""
Make JSON histroy file with recently played video path and timestamp
"""
def write_json_history(entry):
    cwd = os.getcwd().replace('\\', '/')
    entry['path'] = re.sub(f"^{cwd}/", '', entry['path'])
    
    with open(json_history_name, 'w') as json_file:
        json.dump(entry, json_file, indent = 4)

"""
Play the video['path'] file from video['time'] seconds in VLC
"""
def play_video(video):
    if os.name == 'nt': # If Windows
       video['path'] = video['path'].replace('/', '\\')
    
    cmd = f"\"{vlc_path}\" --start-time={video['time']}.0 \"{video['path']}\" --fullscreen"

    subprocess.run(cmd, shell=True)

# Main

video_to_play = get_video_to_play()

if video_to_play != None:
    play_video(video_to_play)

    recently_played = get_recently_played()
    write_json_history(recently_played)
else:
    print("There are no videos to play in this directory")