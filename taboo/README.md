## Taboo Bot

This bot manages a game of taboo in which participants have to guess a word that another is trying to explain. The explaining participants sees the target word and a number of words she cannot use while explaining. The bot keeps track of the score and intervenes in case a forbidden word was used.

## Setting up and running the Taboo bot

### Setup

1. Install [Docker](https://docs.docker.com/get-docker/). You might also need the [jq package](https://stedolan.github.io/jq/download/) too.
2. Clone the [slurk](https://github.com/clp-research/slurk) repository.
3. Before running the bot, several environmental variables would need to be generated and assigned. This process is explained in the [documentation](https://clp-research.github.io/slurk/slurk_gettingstarted.html), which details both the general preparation and the [bot specific initialisations](https://clp-research.github.io/slurk/slurk_gettingstarted.html#chatting-with-a-bot). The bot also needs to have specific permissions, listed below this paragraph. The above permissions can be found in [this example permissions file](https://github.com/clp-research/slurk-bots/blob/master/taboo/data/taboo_bot_permissions.json) already.
    ```
    {
        "api": true,
        "send_privately": true,
        "send_message": true
    }
    ```
4. Make sure that the [slurk](https://github.com/clp-research/slurk) and slurk-bots repositories live next to each other on the same level.
5. Navigate to the base directory of the slurk-bots repository and run the script to launch this bot, your command should look like this:
 ```$ python start_bot.py taboo/ --users 2 --dev --waiting-room-layout-dict taboo/data/waiting_room_layout.json --extra-args taboo/args.ini```.
 This script will build and run the docker images, it will initialise all the env variables with the right permissions and it will set everything up for testing locally on your computer. The bot will appear in your containers list as ```slurk/taboo```.

### Running and playing the bot

If you have everything already set up, you can run the bot using the following command (take notice of the right env variable names):    
```bash
docker run \
    --net="host" \
    -e TABOO_DATA=data/taboo_words.json \
    -e BOT_TOKEN=$TABOO_BOT_TOKEN \
    -e BOT_ID=$TABOO_BOT \
    -e WAITING_ROOM=$WAITING_ROOM \
    -e TASK_ID=$TASK_ID \
    -e SLURK_PORT=5000 \
    -d slurk/taboo
```

Game data – a list of words to guess – is supplied via a json file that has the following pattern:

```json
{
  "Applesauce": [
    "fruit",
    "tree",
    "glass",
    "preserving"
  ],
  "Beef patty": [
    "pork",
    "ground",
    "steak"
  ],
  ...
}
```

Example data can be downloaded with:

```shell
wget https://raw.githubusercontent.com/Kovah/Taboo-Data/main/src/data/en/food.json
```
