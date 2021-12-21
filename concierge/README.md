## Concierge Bot

This is a bot that is able to group users and move them into a newly created room. The bot is composed of one main event handler:
* `on_status`: Listen to 'join' and 'leave' events signalling when a user entered or left the room where the bot is positioned, for experiment settings this will be some kind of waiting room. Once there are enough users for a task, they will be moved to a new room to perform the assigned task.

**Run with docker (recommended)**
The bot can be run with a command that follows the pattern:
```bash
docker run -e SLURK_TOKEN=79d0ea16-d724-463d-9567-1500f716efed -e SLURK_USER=2 -e SLURK_PORT=5000 --net="host" slurk/concierge-bot
```

**Run without docker**
Without docker, bots need to be started from the *slurk-bots* repository as follows:
```bash
python -m concierge --token 79d0ea16-d724-463d-9567-1500f716efed --user 2 --port 5000
```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api`, `send_html_message` and `send_privately`
Please refer to <https://clp-research.github.io/slurk/slurk_multibots.html> for more detailed information.