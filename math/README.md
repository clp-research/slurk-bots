## Math Bot

This is a bot that moderates a simple math question and answer session between two players. The bot is composed of two main methods:
* `on_command`: provides interface for users to create and answer math questions.
* `on_new_task_room`: listen when new task room is created and join the room as bot.

To run the bot, you can build the bot and run the following command:
```bash
docker run -e TOKEN=$MATH_BOT_TOKEN -e MATH_TASK_ID=$TASK_ID --net="host" math-bot
```

where `MATH_BOT_TOKEN` and `TASK_ID` are assumed to already exist.