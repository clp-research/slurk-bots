## Minimal Bot

This is a bot that prints out conversation logs in a room. The bot is composed of a single method:
* `on_joined_room`: when joining a room, try to get information about the user and the room, and prints out message sent by that particular user.

To run the bot, you can run the following command:
```bash
docker run -e TOKEN=$MINIMAL_BOT_TOKEN --net="host" slurk/minimal-bot
```

where `$MINIMAL_BOT_TOKEN` is assumed to already exist.