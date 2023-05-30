# slurk-bots
Bots for the [Slurk](https://github.com/clp-research/slurk) project.

Inside each folder you will find a bot with the instructions to run it locally on your machine.  
If you want to write your own bot and are looking for a good place to start, take a look at the [echo bot](https://github.com/clp-research/slurk-bots/tree/master/echo)

## start a bot

To start any bot you can use the `start_bot.py` script. The script can be used to either start a bot locally alongside a slurk server for developing purposes as well as deploy a bot in a production environment.

### Synopsis
```
usage: start_bot.py [-h] [--extra-args EXTRA_ARGS] [--bot-name BOT_NAME] --users USERS [--slurk-host SLURK_HOST] [--slurk-api-token SLURK_API_TOKEN] [--waiting-room-id WAITING_ROOM_ID] [--waiting-room-layout-id WAITING_ROOM_LAYOUT_ID] [--tokens] [--dev] [--copy-plugins] bot

positional arguments:
  bot                   path to the directory containing your bot

options:
  -h, --help            show this help message and exit
  --extra-args EXTRA_ARGS
                        path to a json file containing extra variable to pass as environment variables to the bot docker (default: None)
  --bot-name BOT_NAME   the name of your bot. If omitted, the name of the directory will be used (default: None)
  --users USERS         number of users for this task (default: None)
  --slurk-host SLURK_HOST
                        api address to your slurk server (default: http://127.0.0.1:5000)
  --slurk-api-token SLURK_API_TOKEN
                        slurk token with api permissions (default: 00000000-0000-0000-0000-000000000000)
  --waiting-room-id WAITING_ROOM_ID
                        room_id of an existing waiting room. With this option will not create a new waiting room (default: None)
  --waiting-room-layout-id WAITING_ROOM_LAYOUT_ID
                        layout_id of an existing layout. With this option will create a new waiting room (default: None)
  --tokens              directly generate tokens to test your bot (default: False)
  --dev                 start a local slurk server for development (default: False)
  --copy-plugins        copy all the files in the plugins directory to slurk's plugins before starting the slurk server (default: False)
```

The folder containing the code of your bot must be passed to the script as positional argument.
The script will take care of building a docker image and starting it.

Other options:
* `--extra-args path/to/extra-arguments.json`: Some bots may need extra arguments which need to be passed to the docker container as environment variable. You can simply save these arguments and their values in a json file and pass it to the script.
* `--bot-name NAME-OF-YOUR-BOT`: if omitted, the script will use the base directory name as name for the bot.
* `--slurk-host http://slurk.your-website.com`: the address of your slurk server. Since the standard value is localhost:5000, you can omit this when developing locally
* `--users N`: the number of users required for this task
* `--slurk-api-token: YOUR-API-TOKEN`: a slurk token with api rights to create a new bot. The standard value is `00000000-0000-0000-0000-000000000000` so you can omit this option when developing locally
* `--waiting-room-id N`: you can reuse an existing waiting room for your bot instead of creating a new one. When this option is passed, the script will not start an additional concierge bot
* `--waiting-room-layout-id N`: similarly to `--waiting-room-id` you can reuse a waiting room layout id, this option will, however, start a concierge bot for the newly created waiting room
* `--tokens`: a token for each user will be generated and printed to the console after starting the bot
* `--dev`: before starting the bot, a slurk server will be started locally for development purposes
* `--copy-pluging`: when this option is used, the script will copy all the files in the `directory-of-your-bot/plugins` directory to the slurk server before starting it


### Assumptions
In order to correctly start your bot the script makes some assumptions about the name of some files needed for your bot to start. These files can be placed anywhere inside the directory containing your bot, but a suggested location would be the `data` directory:
* `task_layout.json`: in this file you should save the layout for your task room. The script will look for a file ending in `.json` containing all the words: `task`, `layout`
* `bot_permissions.json`: the file containing the permissions right for your bot. The script will look for a file ending in `.json` containing all the words: `bot`, `permissions`
* `user_permissions.json`: the file containing the permissions right for your bot. The script will look for a file ending in `.json` containing all the words: `user`, `permissions`
