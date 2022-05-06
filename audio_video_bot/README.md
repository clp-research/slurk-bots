## Audio Video Bot

This bot demonstrates how to use the audio and video functionality provided by slurk.

The demo task shows a button to both participants. Once a user clicks the
button, she gets a private message from the bot and the button disappears.

The setup can be run locally by using the setup.sh script from the slurk/
directory[^1]. It will start slurk, openvidu and the bot and print a user token
for logging in.

Before running the script, you need to set the environment variables
`SLURK_OPENVIDU_URL` and `SLURK_OPENVIDU_SECRET`.

The bot also starts a recording and stops it as soon as one of the users leave.

Running `setup_audio_video_room.sh` from the slurk/ directory will directly lead
to a room, skipping the waiting room setup and clicking the button won't do
anything. No recording is started.

[^1] This assumes that the slurk/ and slurk-bots/ are located in the same parent directory.
