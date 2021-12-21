## Box Bot

This bot demonstrates how to use the functionality provided by the `bounding-boxes` script. It is a copy of the Click Bot (in which the user clicks on objects rather than drawing a box around them).

After being moved to the task room, the user is shown a button that they can use to start the game.
While the game is running, an image is displayed on the right side of the page. This image contains different objects that are described to the user one at a time. The user will only hear each audio once. They then have to draw a box around the described object. They may also choose to skip this item by clicking the button at the top of the page. If the user has answered correctly, this same button will also bring them to the next item.

**Run with docker (recommended)**
The bot can be run with a command that follows the pattern:
```bash
docker run -e SLURK_TOKEN=aaeed04f-123c-454f-b164-4ada17bfe803 -e SLURK_USER=2 -e SLURK_PORT=5000 -e BOX_TASK_ID=1 -e BOX_DATA="boxbot/test_items/shape-colors.json" --net="host" slurk/box-bot
```

**Run without docker**
Without docker, bots need to be started from the *slurk-bots* repository as follows:
```bash
python -m boxbot --token aaeed04f-123c-454f-b164-4ada17bfe803 --user 2 --port 5000 --task 1 --data "boxbot/test_items/shape-colors.json"
```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api`, `send_message`, and `receive_bounding_box`.
A user in this task has to be given the rights: `send_command`
Please refer to <https://clp-research.github.io/slurk/slurk_multibots.html> for more detailed information.

The bot can be started by calling the setup.sh script from the slurk-bots/ directory.
