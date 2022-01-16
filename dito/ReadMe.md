### DiTo Bot: Let's Spot the **Di**fference - **To**gether!
The setting is that agent A sees a picture, and separately, agent B also sees a picture; the task for the agents then is to determine, via exchanging messages, whether they are looking at the same picture or not.

This task can be divided into the following task phases:
1. Waiting for both players to get ready.
2. Presenting each of the two players one out of a pair of pictures.
3. Let both players discuss.
4. Collect their decision on whether the pictures are different. In one task variant one may also require them to provide a description of the suspected difference.


For this purpose the following commands are defined to manage the transition between task phases:
+ */ready* : Both players have to send this command in order to move from phase 1 to phase 2
+ */difference* or */done* : Indicates that the players think they have come to a conclusion. */difference* requires an additional description of the difference.

#### Run the Bot
To run the bot, you can run the following command:
```bash
docker run -e SLURK_TOKEN=$DITO_BOT_TOKEN -e SLURK_USER=$DITO_BOT -e SLURK_WAITING_ROOM=$WAITING_ROOM -e DITO_TASK_ID=$TASK_ID -e SLURK_PORT=5000 --net="host" slurk/dito-bot &
```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api`, `send_html_message` and `send_privately`.
Users assigned to this task need at least the rights: `send_message` and `send_command`
Please refer to the slurk documentation for more detailed information.


#### Modifications
Under `lib/config.py` you find a number of global variables that define experiment settings as well as short descriptions of their effect on the experiment.

Image pairs for the task should be specified one pair per line
in the `image_data.csv`. The components of a pair are separated by
a comma followed by no whitespace.


#### Versions
A variant of this bot compatible with slurk v2 can be accessed under the name `cola` in branch `2.0.0`. This older version comes with an AMT connector part.

