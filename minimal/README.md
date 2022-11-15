## Minimal Bot
This bot serves as a minimal example demonstrating a subset of the most important functionalities available and how to use them in this context.
The bot is composed of a single event handler but others can be added in a similar fashion:
* `on_joined_room`: When joining a room, the bot tries to retrieve information about itself, it will use those for an introduction. Finally, it will retrieve and print all logs assigned to its room and user id.

To run the bot, you can run a command in a similar fashion as:
```bash
docker run -e SLURK_TOKEN=d8fb2d9a-8afe-43c3-87b5-2c934596907f -e SLURK_USER=2 -e SLURK_PORT=5000 --net="host" slurk/minimal-bot
```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api`, `send_message`
Please refer to [the documentation](https://clp-research.github.io/slurk/slurk_multibots.html) for more detailed information.
