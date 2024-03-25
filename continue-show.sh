#!/usr/bin/env bash

script_dir="$(realpath $(dirname $(readlink -f $0)))"
script_path="${script_dir}/continue.py"
vlc_conf_path="$HOME/.config/vlc/vlc-qt-interface.conf"
vlc_path="/usr/bin/vlc"

python3 $script_path -v $vlc_path $vlc_conf_path
