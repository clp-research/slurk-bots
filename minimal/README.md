## Minimal Bot
This bot serves as a minimal example demonstrating a subset of the most import functionalities available and how to use them in this context.
The bot is composed of a single event handler but others can be added in a similar fashion:
* `on_joined_room`: When joining a room, the bot tries to retrieve information about itself, it will use those for an introduction. Finally, it will retrieve and print all logs assigned to its room and user id.

To run the bot, you can run the following command:
```bash
docker run -e TOKEN=$MINIMAL_BOT_TOKEN --net="host" slurk/minimal-bot
```

Where `$MINIMAL_BOT_TOKEN` can be obtained with `scripts/create_token.sh`.
The token has to be linked to a permissions entry that gives the bot at least the following rights: `api`, `send_message`
Please refer to <https://clp-research.github.io/slurk/slurk_multibots.html> for a more detailed information.