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


class PlayLocation:
    path: str
    time: int

    def __init__(self, path, time):
        self.path = path
        self.time = time


class VlcHistory:
    def __init__(self, ini_path):
        self.path = ini_path
        self.config = self._read_config(self.path)

    def refresh(self):
        """Read the history again"""
        self.config = self._read_config(self.path)

    def get_recently_played(self) -> PlayLocation:
        """
        return: recently played video which from current directory from
                VLC history file if there is such video in the history
                None if there is no such file in the history
        """
        cwd = os.getcwd().replace("\\", "/")  # For Windows paths

        history = self._get_history()

        for entry in history:
            if entry.path.startswith(f"{cwd}/"):
                path = entry.path.removeprefix(f"{cwd}/")
                return PlayLocation(path, entry.time)

        return None

    @staticmethod
    def _read_config(ini_path) -> RawConfigParser:
        try:
            config = RawConfigParser()  # https://stackoverflow.com/a/2538141/2721340
            config.read(ini_path)
            return config
        except:
            print(f"VLC history file '{ini_path}' does not exist.")
            return None

    @staticmethod
    def _path_prefix() -> str:
        if os.name == "nt":  # If Windows
            return "file:///"
        # If Linux ('posix')
        return "file://"

    def _get_history(self) -> list[PlayLocation]:
        if not self.config:
            return []

        # Remove trailing commas
        self.config["RecentsMRL"]["list"].rstrip(",")
        self.config["RecentsMRL"]["times"].rstrip(",")

        # Split
        paths = self.config["RecentsMRL"]["list"].split(", ")
        paths = [path.replace(self._path_prefix(), "") for path in paths]
        paths = [urllib.parse.unquote(path) for path in paths]

        times = self.config["RecentsMRL"]["times"].split(", ")
        times = [int(time) // 1000 for time in times]

        return [PlayLocation(path, time) for path, time in zip(paths, times)]


class JsonHistory:
    def __init__(self, json_path):
        self.path = json_path

    def get_recently_played(self) -> PlayLocation:
        """
        return: recently played video from own history file
                None if history file does not exist
        """
        recently_played = self._read_json()

        if not recently_played:
            return None

        return PlayLocation(recently_played["path"], recently_played["time"])

    def save_history(self, location: PlayLocation):
        """
        Make JSON histroy file with recently played video path and timestamp
        """
        entry = {"path": location.path, "time": location.time}

        with open(self.path, "w") as json_file:
            json.dump(entry, json_file, indent=4)

    def _read_json(self) -> dict:
        try:
            with open(self.path) as json_file:
                return json.load(json_file)
        except:
            print(f"JSON history file {self.path} does not exist")
            return None


class VlcPlayer:
    def __init__(self, vlc_path):
        self.vlc_path = vlc_path

    def play(self, location: PlayLocation):
        """
        Play the 'path' file from 'time' seconds in VLC
        """
        if os.name == "nt":  # If Windows
            video_path = location.path.replace("/", "\\")

        cmd = [
            self.vlc_path,
            f"--start-time={location.time}.0",
            video_path,
            "--fullscreen",
            # "--play-and-exit",
        ]

        subprocess.run(cmd, shell=True, check=False)


class VideoLister:
    FILE_NAME_REGEX = "^.+\\.(mp4|mkv|avi|webm)$"

    def __init__(self, path):
        self.path = path

    def list_videos(self) -> list[str]:
        """
        return: The list of videos' path in the current directory
                and its subdirectories (in alphabetical order)
        """
        files = self._list_recursively(self.path)

        pattern = re.compile(self.FILE_NAME_REGEX)
        videos = list(filter(pattern.match, files))

        # Remove samples
        wo_samples = [v for v in videos if "sample" not in v.lower()]
        if wo_samples:
            videos = wo_samples

        # Replace Windows path backslashes
        return [video.replace("\\", "/") for video in videos]

    def _list_recursively(self, path) -> list[str]:
        """
        List all files in a directory tree with relative path
        (ext4 does not return file names sorted)
        """
        dir_list = list(os.walk(path))[0]
        subdirs = sorted(dir_list[1])
        files = sorted(dir_list[2])

        file_list = []

        for subdir in subdirs:
            for file in self._list_recursively(f"{path}/{subdir}"):
                file_list.append(f"{subdir}/{file}")

        return file_list + files


class VideoChooser:
    def __init__(self, json_hst: JsonHistory, vlc_hst: VlcHistory):
        self.json_hst = json_hst
        self.vlc_hst = vlc_hst

    def get_video_to_play(self) -> PlayLocation:
        """
        return: recently played video if it wasn't finished
                next video if recently played video was finished
        """
        entry = self._get_recently_played()
        videos = VideoLister(".").list_videos()

        if entry:
            if entry.time != 0:
                video_to_play = entry
            else:
                i_recent = 0

                for i, video in enumerate(videos):
                    if video == entry.path:
                        i_recent = i
                        break

                video_to_play = PlayLocation(videos[(i_recent + 1) % len(videos)], 0)
        elif len(videos) > 0:
            video_to_play = PlayLocation(videos[0], 0)
        else:
            return None

        return video_to_play

    @staticmethod
    def _get_latter(loc1: PlayLocation, loc2: PlayLocation) -> PlayLocation:
        """Return the item which is latter in alphabetical order or time"""
        if loc1.path > loc2.path:
            return loc1

        if loc2.path > loc1.path:
            return loc2

        if loc1.time > loc2.time:
            return loc1

        return loc2

    def _get_recently_played(self) -> PlayLocation:
        """
        return: latter recently played video from VLC history or from own history file
                if both do exist the existing one if only one of them exists
                None if both lookups are unsuccessful
        """
        recently_played_json = self.json_hst.get_recently_played()
        recently_played_vlc = self.vlc_hst.get_recently_played()

        if recently_played_json and recently_played_vlc:
            return self._get_latter(recently_played_json, recently_played_vlc)

        if recently_played_json:
            return recently_played_json

        if recently_played_vlc:
            return recently_played_vlc

        return None


def main():
    if len(sys.argv) != 3:
        print("Argument error!")
        script_name = os.path.basename(__file__)
        print(f"Usage: python3 {script_name} [vlc_path] [vlc_history_file_path]")
        sys.exit()

    vlc_path = sys.argv[1]
    vlc_history_path = sys.argv[2]

    json_hst = JsonHistory("recently_played.json")
    vlc_hst = VlcHistory(vlc_history_path)

    video_to_play = VideoChooser(json_hst, vlc_hst).get_video_to_play()

    if video_to_play:
        VlcPlayer(vlc_path).play(video_to_play)

        vlc_hst.refresh()
        recently_played = vlc_hst.get_recently_played()
        json_hst.save_history(recently_played)
    else:
        print("There are no videos to play in this directory")


if __name__ == "__main__":
    main()
