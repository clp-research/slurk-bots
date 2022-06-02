## Audio Video Setup

This directory contains a minimal setup for the audio and video functionality
provided by slurk.

The setup can be run locally by using the setup_audio_video_room.sh script
from the slurk/ or from the slurk-bots/ directory[^1]. It will start slurk
with openvidu and print user tokens for logging in. No recording is started.

Before running the script, you need to set the environment variables
`SLURK_OPENVIDU_URL` and `SLURK_OPENVIDU_SECRET`.

[^1] This assumes that the slurk/ and slurk-bots/ are located in the same parent directory.
