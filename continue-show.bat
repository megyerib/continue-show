@echo off

set script_dir=%~dp0
set script_path=%script_dir%continue_show_vlc.py
set vlc_ini_path=%APPDATA%\vlc\vlc-qt-interface.ini
set vlc_path="C:\Program Files\VideoLAN\VLC\vlc.exe"

python %script_path% %vlc_path% %vlc_ini_path%
