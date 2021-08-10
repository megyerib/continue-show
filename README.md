# Continue your TV series where you left off

## How it works

1. The script scans the VLC history. If any video from the working directory or its subdirectories is there it continues from the most recent.
2. If no videos from the working directory were found in the VLC history (it is about 30 entries long so a video can run out of it) then the script scans for a history file made by itself in the root of the working directory.
3. If the previous attempt was unsuccessful too, the first video file will be played.

## How to use (Windows)

1. Navigate to the ditrectory with the video files. It can contain subdirectories as well, the script scans them, too.
2. Run the `continue-show.bat` script. You can create another batch script in this directory to call it as well.

## Limitations

VLC stores a timestamp for each video it has played. It indicates where they were left off. If a video was finished then its timestamp is 0. This is the case if it was left off in the first two minutes as well, therefore the script can't distinguish the two states. If a video was left off in the first two minutes, then the next one will be played when the script is called again.
 