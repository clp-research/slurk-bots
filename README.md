# slurk-bots
Bots for the [Slurk](https://github.com/clp-research/slurk) project.

Inside each folder you will find a bot with the instructions to run it locally on your machine.  
If you want to write your own bot and are looking for a good place to start, take a look at the [echo bot](https://github.com/clp-research/slurk-bots/tree/master/echo)

## start a bot

To start any bot you can use the `start_bot.py` script. The script can be used to either start a bot locally alongside a slurk server for developing purposes as well as deploy a bot in a production environment.

### Synopsis
```
usage: start_bot.py [-h] [--extra-args EXTRA_ARGS] [--bot-name BOT_NAME] --users USERS [--slurk-host SLURK_HOST] [--slurk-api-token SLURK_API_TOKEN] [--credentials-from-file CREDENTIALS_FROM_FILE] [--waiting-room-id WAITING_ROOM_ID] [--waiting-room-layout-id WAITING_ROOM_LAYOUT_ID] [--waiting-room-layout-dict WAITING_ROOM_LAYOUT_DICT] [--tokens] [--dev] [--copy-plugins]
                    bot

positional arguments:
  bot                   path to the directory containing your bot

options:
  -h, --help            show this help message and exit
  --extra-args EXTRA_ARGS
                        path to a configuration file containing extra variable to pass as environment variables to the bot docker (default: None)
  --bot-name BOT_NAME   the name of your bot. If omitted, the name of the directory will be used (default: None)
  --users USERS         number of users for this task (default: None)
  --slurk-host SLURK_HOST
                        api address to your slurk server (default: http://127.0.0.1:5000)
  --slurk-api-token SLURK_API_TOKEN
                        slurk token with api permissions (default: 00000000-0000-0000-0000-000000000000)
  --credentials-from-file CREDENTIALS_FROM_FILE
                        read slurk host and api token from a json file (default: None)
  --waiting-room-id WAITING_ROOM_ID
                        room_id of an existing waiting room. With this option will not create a new waiting room or a concierge bot (default: None)
  --waiting-room-layout-id WAITING_ROOM_LAYOUT_ID
                        layout_id of an existing layout for a waiting room. (default: None)
  --waiting-room-layout-dict WAITING_ROOM_LAYOUT_DICT
                        path to a json file containing a layout for a waiting room (default: concierge/waiting_room_layout.json)
  --tokens              generate and print tokens to test your bot (default: False)
  --dev                 start a local slurk server for development (default: False)
  --copy-plugins        copy all the files in the plugins directory to slurk's plugins before starting the slurk server (default: False)
```

The folder containing the code of your bot must be passed to the script as positional argument.
The script will take care of building a docker image and starting it.

Other options:
* `--extra-args path/to/extra-arguments.ini`: Some bots may need extra arguments which need to be passed to the docker container as environment variable. You can simply save these arguments and their values in a configuration file (.ini) and pass it to the script.
* `--bot-name NAME-OF-YOUR-BOT`: if omitted, the script will use the base directory name as name for the bot.
* `--slurk-host https://slurk.your-website.com`: the address of your slurk server. Since the standard value is localhost:5000, you can omit this when developing locally.
* `--users N`: the number of users required for this task.
* `--slurk-api-token: YOUR-API-TOKEN`: a slurk token with api rights to create a new bot. The standard value is `00000000-0000-0000-0000-000000000000` so you can omit this option when developing locally.
* `--credentials-from-file`: read slurk host and api token from a configuration file. See the Assumptions session for more information about the formatting for the credentials file.
* `--waiting-room-id N`: you can reuse an existing waiting room for your bot instead of creating a new one. When this option is passed, the script will not start an additional concierge bot.
* `--waiting-room-layout-id N`: similarly to `--waiting-room-id` you can reuse a waiting room layout id, this option will, however, start a concierge bot for the newly created waiting room.
* `--waiting-room-layout-dict`: with this argument you can specify which layout file you want to load for your waiting room. The default value will use the layout in the `concierge` directory.
* `--tokens`: a token for each user will be generated and printed to the console after starting the bot.
* `--dev`: before starting the bot, a slurk server will be started locally for development purposes.
* `--copy-plugins`: when this option is used, the script will copy all the files in the `directory-of-your-bot/plugins` directory to the slurk server before starting it. This option can only be used if `--dev` is also passed as argument. The script cannot copy the plugins to an already running instance of the slurk server, you will have to do this manually with the `docker cp` command.


### Assumptions
In order to correctly start your bot the script makes some assumptions about the name of some files needed for your bot to start. These files can be placed anywhere inside the directory containing your bot, but a suggested location would be the `data` directory:
* `task_layout.json`: in this file you should save the layout for your task room. The script will look for a file ending in `.json` containing all the words: `task`, `layout`
* `bot_permissions.json`: the file containing the permissions for your bot. The script will look for a file ending in `.json` containing all the words: `bot`, `permissions`
* `user_permissions.json`: the file containing the permissions for your bot. The script will look for a file ending in `.json` containing all the words: `user`, `permissions`


#### Extra arguments file
The file containing the extra variables for your bot must follow the following formatting:
```
[ARGS]
IMPORTANT_VARIABLE = Hello
OTHER_VARIABLE = World 
```

#### Credentials file
Instead of passing the address of your slurk server and an API-Token to the script as single arguments, you can instead use the `--credentials-from-file` option to pass a configuration file containing this information. Your file must have the following formatting:
```
[SLURK CREDENTIALS]
host = https://slurk.your-website.com
token = 00000000-0000-0000-0000-000000000000
```

### Examples
Start the echo bot alongside with a slurk server and a concierge bot. A token for testing will also be generated by the script:  
`$ python start_bot.py echo/ --users 1 --tokens --dev`

output: 
```
---------------------------
waiting room id:	1
task id:		      1
---------------------------
Token: 6aeb2b62-4f7b-49d8-92e0-448af0bee055 | Link: http://127.0.0.1:5000/login?name=user_0&token=6aeb2b62-4f7b-49d8-92e0-448af0bee055

```

The script will print out the waiting room id as well as the task id since this information is needed to generate new tokens for users.
If the `--token` option was used, the script will also generate one token for each user. You can either copy the token and choose your own user name or directly open the link to automatically log into slurk with the generated token.

Once your local slurk server is already running, you can start a new bot and recycle the waiting room and concierge bot that are already running:  
`$  python start_bot.py clickbot/ --users 1 --tokens --waiting-room-id 1 --extra-args clickbot/args.ini`

Once your bot is ready and you want to deploy on your production slurk server you can pass the arguments `--slurk-host` and `--slurk-api-token`:  
```
$ python start_bot.py echo/ --users 1 --tokens \
    --slurk-host https://slurk.mywebsite.com \
    --slurk-api-token 01234567-8901-2345-6789-012345678901
```
or save your credentials in a configuration file and pass this as an argument to the script:  
`$ python start_bot.py echo/ --users 1 --tokens --credentials-from-file path/to/credentials.ini`
