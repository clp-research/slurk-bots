## Minimal Bot
This bot serves as a minimal example demonstrating a subset of the most important functionalities available and how to use them in this context.
The bot is composed of a single event handler but others can be added in a similar fashion:
* `on_joined_room`: When joining a room, the bot tries to retrieve information about itself, it will use those for an introduction. Finally, it will retrieve and print all logs assigned to its room and user id.

**Run with docker (recommended)**
The bot can be run with a command that follows the pattern:
```bash
docker run -e SLURK_TOKEN=6cc15da2-d272-4e5d-9ebf-f67d380e81ba -e SLURK_USER=1 -e SLURK_PORT=5000 --net="host" slurk/minimal-bot
```

**Run without docker**
Without docker, bots need to be started from the *slurk-bots* repository as follows:
```bash
python -m minimal --token 6cc15da2-d272-4e5d-9ebf-f67d380e81ba --user 1 --port 5000
```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api`, `send_message`
Please refer to <https://clp-research.github.io/slurk/slurk_multibots.html> for more detailed information.

