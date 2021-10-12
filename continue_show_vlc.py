"""
Continue video series from the most recent location.
"""

import os
import sys
import re
import json
import urllib.parse
import subprocess
from configparser import RawConfigParser

# Arguments
if len(sys.argv) < 3:
    print("Missing argument!")
    script_name = os.path.basename(__file__)
    print(f"Usage: python {script_name} [vlc_path] [vlc_history_file_path]")
    sys.exit()

vlc_path = sys.argv[1]
vlc_history_path = sys.argv[2]

# Constants
VALID_FILE_TYPES = {"mp4", "mkv", "avi"}
JSON_HISTORY_FILE = "recently_played.json"


def list_recursively(path):
    """
    List all files in a directory tree with relative path
    (ext4 does not return file names sorted)
    """
    dir_list = list(os.walk(path))[0]

    subdirs = sorted(dir_list[1])
    files = sorted(dir_list[2])

    file_list = []

    for subdir in subdirs:
        for file in list_recursively(f"{path}/{subdir}"):
            file_list += f"{subdir}/{file}"

    file_list += files

    return file_list


def list_videos():
    """
    return: The list of videos in the current directory and its subdirectories
    """
    files = list_recursively(".")

    re_object = re.compile(f".+\\.({'|'.join(VALID_FILE_TYPES)})$")  # File type filter
    videos = list(filter(re_object.match, files))

    # Replace Windows path backslashes
    return [video.replace("\\", "/") for video in videos]


def list_vlc_history(path):
    """
    path:   VLC ini file path

    return: VLC history list [{path (abs), time}]; newest to oldest
    """
    config = RawConfigParser()  # https://stackoverflow.com/a/2538141/2721340

    try:
        config.read(path)
    except:
        print(f"VLC history file '{path}' does not exist.")
        return []

    try:
        # Remove trailing commas
        if config["RecentsMRL"]["list"][-1] == ",":
            config["RecentsMRL"]["list"] = config["RecentsMRL"]["list"][:-1]
            config["RecentsMRL"]["times"] = config["RecentsMRL"]["times"][:-1]

        # Split
        if os.name == "nt":  # If Windows
            path_prefix = "file:///"
        else:  # If Linux ('posix')
            path_prefix = "file://"

        paths = [
            path.replace(path_prefix, "")
            for path in config["RecentsMRL"]["list"].split(", ")
        ]
        times = [
            int(int(time) / 1000) for time in config["RecentsMRL"]["times"].split(", ")
        ]
    except:
        print("History cannot be read from VLC history file.")
        return []

    return [
        {"path": urllib.parse.unquote(paths[i]), "time": times[i]}
        for i in range(0, len(paths))
    ]


def get_recently_played_from_vlc_history():
    """
    return: recently played video which is located in the current directory from VLC history file
            {path, time} if there is such video in the history
            None if there is no such file in the history
    """
    cwd = os.getcwd().replace("\\", "/")  # For Windows paths

    pattern = re.compile(f"^{cwd}/.+")

    history = list_vlc_history(vlc_history_path)

    for entry in history:
        if pattern.match(entry["path"]):
            return entry

    return None


def get_recently_played_from_json(path):
    """
    return: recently played video from own history file {path (absolute), time}
            None if history file does not exist
    """
    try:
        with open(path) as json_file:
            entry = json.load(json_file)
            cwd = os.getcwd().replace("\\", "/")
            entry["path"] = f"{cwd}/{entry['path']}"
            return entry
    except:
        print("JSON history file does not exist")

    return None


def get_latter(time1: dict, time2: dict) -> dict:
    """Return the item which is latter in alphabetical order or time"""
    if time1["path"] > time2["path"]:
        return time1

    if time2["path"] > time1["path"]:
        return time2

    if time1["time"] > time2["time"]:
        return time1

    return time2


def get_recently_played():
    """
    return: latter recently played video from VLC history or from own history file if both do exist
            the existing one if only one of them exists
            None if both lookups are unsuccessful
    """
    recently_played_json = get_recently_played_from_json(JSON_HISTORY_FILE)
    recently_played_vlc = get_recently_played_from_vlc_history()

    if recently_played_json and recently_played_vlc:
        return get_latter(recently_played_json, recently_played_vlc)

    if recently_played_json:
        return recently_played_json

    if recently_played_vlc:
        return recently_played_vlc

    return None


def get_video_to_play():
    """
    return: recently played video if it wasn't finished
            next video if recently played video was finished
    """
    entry = get_recently_played()
    videos = list_videos()

    if entry:
        if entry["time"] != 0:
            video_to_play = entry
        else:
            cwd = os.getcwd().replace("\\", "/")

            i_recent = 0

            for i, video in enumerate(videos):
                if f"{cwd}/{video}" == entry["path"]:
                    i_recent = i
                    break

            video_to_play = {"path": videos[(i_recent + 1) % len(videos)], "time": 0}
    elif len(videos) != 0:
        video_to_play = {"path": videos[0], "time": 0}
    else:
        return None

    return video_to_play


def write_json_history(entry):
    """
    Make JSON histroy file with recently played video path and timestamp
    """
    cwd = os.getcwd().replace("\\", "/")
    entry["path"] = re.sub(f"^{cwd}/", "", entry["path"])

    with open(JSON_HISTORY_FILE, "w") as json_file:
        json.dump(entry, json_file, indent=4)


def play_video(video):
    """
    Play the video['path'] file from video['time'] seconds in VLC
    """
    if os.name == "nt":  # If Windows
        video["path"] = video["path"].replace("/", "\\")

    cmd = f"\"{vlc_path}\" --start-time={video['time']}.0 \"{video['path']}\" --fullscreen"

    subprocess.run(cmd, shell=True, check=False)


def main():
    video_to_play = get_video_to_play()
    print("To be played")
    print(video_to_play)

    if video_to_play:
        play_video(video_to_play)

        recently_played = get_recently_played_from_vlc_history()
        write_json_history(recently_played)
    else:
        print("There are no videos to play in this directory")


if __name__ == "__main__":
    main()
