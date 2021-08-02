## Math Bot

This is a bot that moderates a simple math question and answer session between two players. The bot is composed of two main methods:
* `on_command`: Provides interface for users to create and answer math questions.
* `on_new_task_room`: Waits for a new task room to be created and joins the room as bot.

To run the bot, you can build the bot and run the following command:
```bash
docker run -e SLURK_TOKEN=$MATH_BOT_TOKEN -e -e SLURK_PORT=5000 MATH_TASK_ID=$TASK_ID --net="host" slurk/math-bot
```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api`, `send_message`, `send_privately`.
Users assigned to this task need at least the rights: `send_command`
Please refer to <https://clp-research.github.io/slurk/slurk_multibots.html> for more detailed information.