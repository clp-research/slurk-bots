## Concierge Bot

This is a bot that is able to group users and move them into a newly created room. The bot is composed of one main method:
* `on_status`: listens to 'join' and 'leave' events signalling when a user entered or left a room, and move them into a new room if there is enough users for a task.

To run the bot, you can run the following command:
```bash
docker run -e TOKEN=$CONCIERGE_BOT_TOKEN --net="host" slurk/concierge-bot
```

where `CONCIERGE_BOT_TOKEN` is assumed to already exist.