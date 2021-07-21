## Echo Bot

This is a bot that repeats what a user typed by sending it back to the individual user (for private messages) or their room. The bot is composed of three methods:
* `on_new_task_room`: triggered once a new task room is created. The bot will join this room if the task id matches the one it is called with.
* `on_text_message`: triggered once a message is sent that the bot can see. If the text message is private, broadcast it back only to the user. If it is public, broadcast it back to the room.
* `on_image_message`: triggered once an image is sent that the bot can see. If the image message is private, broadcast it back only to the user. If it is public, broadcast it back to the room.

The bot can be run with a command that follows the pattern:
```bash
docker run -e SLURK_TOKEN=c8469175-8e34-4c69-a2c7-472edce424b3 -e SLURK_USER=1 -e SLURK_PORT=5000 -e ECHO_TASK_ID=1 --net="host" slurk/echo-bot
```

The token needs to have atleast the permissions `send_privately` and `send_message`. Please refer to <https://clp-research.github.io/slurk/slurk_multibots.html> for more detailed information.