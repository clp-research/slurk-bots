### Wordle Bot: Play wordle with images!
Two people come together to play wordle together with a twist: they also get an extra hint in the shape of a picture. The players can discuss as long as they want before entering their guess, but they must coordinate as the Bot will only accept a guess if both players agree.

#### Run the Bot
Before you start the Bot it is important to copy the javascript file responsible for the wordle interface to slurk's plugins:
* copy ```wordle.js``` to ```slurk/slurk/views/static/plugins```

To run the bot, you can run the following command:
```bash
docker run -e SLURK_TOKEN=$WORDLE_BOT_TOKEN -e SLURK_USER=$WORDLE_BOT -e SLURK_WAITING_ROOM=$WAITING_ROOM -e WORDLE_TASK_ID=$TASK_ID -e SLURK_PORT=5000 --net="host" slurk/wordle-bot &
```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api`, `send_html_message`, `send_command` and `send_privately`.
Users assigned to this task need at least the rights: `send_message` and `send_command`
Please refer to the slurk documentation for more detailed information.


#### Modifications
Under `lib/config.py` you find a number of global variables that define experiment settings as well as short descriptions of their effect on the experiment.

Word/image pairs should be specified in a tab separated file: ```data/image_data.tsv```. The components of a pair are separated by a tab in the order: word tab link-to-image
