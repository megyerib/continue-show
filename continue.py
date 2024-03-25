#!/usr/bin/env python3

"""
Continue to play the recently played video in the working directory.
History is loaded from vlc.ini and a local json file (JSON_HST_PATH)
"""

import argparse
from configparser import RawConfigParser
import logging
import os
import json
import subprocess
from typing import Optional, TypeAlias
import urllib.parse
import pathlib

JSON_HST_PATH = "recently_played.json"
SUPPORTED_FILE_TYPES = "mp4 mkv avi webm".split(" ")

logger = logging.getLogger(__name__)

timestamp: TypeAlias = tuple[str, int]


def configure_logger(*, verbose):
    logging.basicConfig(
        format="[%(asctime)s.%(msecs)03d] %(filename)s:%(lineno)d [%(levelname).1s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG if verbose else logging.ERROR,
    )


def get_json_history() -> Optional[timestamp]:
    if not os.path.exists(JSON_HST_PATH):
        logger.debug("No JSON history file (%s) found", JSON_HST_PATH)
        return None
    with open(JSON_HST_PATH, "r", encoding="utf8") as f:
        hst = json.load(f)
    try:
        ret = (hst["path"], hst["time"])
        logger.debug("Most recent video in %s: %s", JSON_HST_PATH, ret)
        return ret
    except Exception as error:
        logger.error("Error while loading %s: %s", JSON_HST_PATH, error)
        return None


def get_vlc_history(vlc_ini_path: str) -> list[timestamp]:
    if not os.path.exists(vlc_ini_path):
        logger.debug("No vlc.ini found: %s", vlc_ini_path)
        return []
    parser = RawConfigParser()
    parser.read(vlc_ini_path)

    paths = parser["RecentsMRL"]["list"].split(", ")
    paths = [path.removeprefix("file://") for path in paths]
    paths = [urllib.parse.unquote(path) for path in paths]

    times = parser["RecentsMRL"]["times"].split(", ")
    times = [int(time) // 1000 for time in times]

    ret = list(zip(paths, times))
    logger.debug("Found %d items in VLC history", len(ret))
    return ret


def get_most_recent_ts(hst: list[timestamp]) -> Optional[timestamp]:
    if len(hst) == 0:
        logger.debug("No video found in vlc.ini")
        return None
    cwd = os.getcwd()
    hst = [ts for ts in hst if ts[0].startswith(cwd) and "sample" not in ts[0].lower()]
    hst.sort()
    if len(hst) == 0:
        logger.debug("No matching video found in vlc.ini")
        return None
    ret = hst[-1]
    ret = (ret[0].removeprefix(cwd + "/"), ret[1])
    logger.debug("Most recent video in vlc.ini: %s", ret)
    return ret


def get_more_recent(ts_1: Optional[timestamp], ts_2: Optional[timestamp]) -> Optional[timestamp]:
    if not (ts_1 or ts_2):
        return None
    if ts_1 and ts_2:
        ret = max(ts_1, ts_2)
    else:
        ret = ts_1 or ts_2
    logger.debug("Most recent video: %s", ret)
    return ret


def get_sorted_videos() -> list[str]:
    ret = []
    for item in pathlib.Path(".").rglob("*.*"):
        path = str(item)
        suffix = path.rsplit(".", maxsplit=1)[-1]
        if os.path.isfile(path) and suffix in SUPPORTED_FILE_TYPES:
            ret.append(path)
    ret.sort()
    return ret


def get_video_to_play(videos: list[str], recent: Optional[timestamp]):
    if not videos:
        logger.error("No videos in this directory")
        return None
    if not recent:
        ret = (videos[0], 0)
    else:
        path = recent[0]
        time = recent[1]
        index = videos.index(path)
        if recent[1] == 0:
            index = (index + 1) % len(videos)
        ret = (videos[index], time)
    logger.debug("Video to play: %s", ret)
    return ret


def vlc_play(vlc_path, video: timestamp):
    cmd = [
        vlc_path,
        "-v",
        f"--start-time={video[1]}.0",
        video[0],
        "--fullscreen",
    ]
    logger.debug(" ".join(cmd))

    subprocess.run(cmd, check=False)


def update_json_hst_file(vlc_ini_path):
    logger.debug("Updating %s...", JSON_HST_PATH)
    vlc_hst = get_vlc_history(vlc_ini_path)
    vlc_recent = get_most_recent_ts(vlc_hst)
    new_recent = {
        "path": vlc_recent[0],
        "time": vlc_recent[1],
    }
    with open(JSON_HST_PATH, "w", encoding="utf8") as f:
        json.dump(new_recent, f, indent=4)
    logger.debug("%s updated", JSON_HST_PATH)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("vlc_path", help="Path of the VLC binary", type=str)
    parser.add_argument("vlc_ini_path", help="Path of vlc.ini", type=str)
    parser.add_argument("-v", "--verbose", help="Verbose log", action="store_true")
    args = parser.parse_args()

    configure_logger(verbose=args.verbose)

    json_recent = get_json_history()
    vlc_hst = get_vlc_history(args.vlc_ini_path)
    vlc_recent = get_most_recent_ts(vlc_hst)
    recent = get_more_recent(json_recent, vlc_recent)

    videos = get_sorted_videos()

    video_to_play = get_video_to_play(videos, recent)
    if not video_to_play:
        logger.error("No video to play!")
        return

    vlc_play(args.vlc_path, video_to_play)

    update_json_hst_file(args.vlc_ini_path)


main()
