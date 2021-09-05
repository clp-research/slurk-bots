## Click Bot

This bot demonstrates how to use the functionality provided by the `mouse-tracking` script.
After being moved to the task room the user is shown a button that they can use to start the game.
While the game is running an image is displayed on the right side of the page. This image contains different objects that are described to the user one at a time. The user will only hear each audio once. They then have to click on the described object. They may also choose to skip this item by clicking the button at the top of the page. If the user has answered correctly this same button will also bring them to the next item.

To run the bot, you can run a command in a similar fashion as:
```bash
docker run -e SLURK_TOKEN="6c2796b1-0c55-4c1d-a379-5d7afe5629c1" -e SLURK_USER=1 -e SLURK_PORT=5000 -e CLICK_DATA="shape-colors.json" -e CLICK_TASK_ID=1 --net="host" slurk/concierge-bot
```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api` and `send_message`
A user in this task has to be given the rights: `send_command`
Please refer to <https://clp-research.github.io/slurk/slurk_multibots.html> for more detailed information.