## Concierge Bot

This is a bot that is able to group users and move them into a newly created room. The bot is composed of one main event handler:
* `on_status`: Listen to 'join' and 'leave' events signalling when a user entered or left the room where the bot is positioned, for experiment settings this will be some kind of waiting room. Once there are enough users for a task, they will be moved to a new room to perform the assigned task.

To run the bot, you can run a command in a similar fashion as:
```bash
docker run \
    --net="host" \
    -e SLURK_TOKEN=$CONCIERGE_BOT_TOKEN \
    -e SLURK_USER=$CONCIERGE_BOT \
    -e SLURK_PORT=5000 \
    -d slurk/concierge-bot

```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api`, `send_html_message` and `send_privately`
Please refer to [the documentation](https://clp-research.github.io/slurk/slurk_multibots.html) for more detailed information.
