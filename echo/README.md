## Echo Bot
This bot parrots user messages. If a private message is sent to the bot by a user, the bot will send it back to this individual user only. Other messages are sent back to the room from where they were received.

* `on_text_message`: triggered for messages containing text
* `on_image_message`: triggered for messages containing images

**Run with docker (recommended)**
The bot can be run with a command that follows the pattern:
```bash
docker run -e ECHO_TOKEN=24e43285-c8ba-44e3-8608-3d91227c9da7 -e ECHO_USER=1 -e SLURK_PORT=5000 -e ECHO_TASK_ID=1 --net="host" slurk/echo-bot
```

**Run without docker**
Without docker, bots need to be started from the *slurk-bots* repository as follows:
```bash
python -m echo --token 24e43285-c8ba-44e3-8608-3d91227c9da7 --user 1 --port 5000 --task 1
```

Tokens and users have to be created beforehand and the appropriate values passed. The above only shows the general pattern and cannot simply be copy-pasted. The token needs to have at least the permissions `api`, `send_privately`, `send_message` and `send_image`. Please refer to <https://clp-research.github.io/slurk/slurk_multibots.html> for more detailed information.
