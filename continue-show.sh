#!/bin/bash

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
script_path="${script_dir}/continue_show_vlc.py"
vlc_conf_path="$(find ~/snap/vlc -name vlc-qt-interface.conf | tail -1)"
vlc_path="vlc"

python3 $script_path $vlc_path $vlc_conf_path
