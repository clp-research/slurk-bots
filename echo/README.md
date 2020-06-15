## Echo Bot

This is a bot that repeat what the users typed back to the room. The bot is composed of three methods:
* `on_new_task_room`: listens when new task room is created and join the room as bot.
* `on_text_message`: listens when the user send a message and broadcast it back to the room. If the text message is private, broadcast it back only to the user.
* `on_image_message`: listens when the user send an image and broadcast it back to the room. If the image message is private, broadcast it back only to the user. 

To run the bot, you can run the following command:
```bash
docker run -e TOKEN=$ECHO_BOT_TOKEN -e ECHO_TASK_ID=$TASK_ID --net="host" slurk/echo-bot
```

where `ECHO_BOT_TOKEN` and `TASK_ID` are assumed to already exist.