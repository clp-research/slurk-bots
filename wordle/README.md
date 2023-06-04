# Wordle Bot: Play wordle with images!

This repository contains the source code for a collaborative Image-Wordle game. It can be run on the [slurk](https://github.com/clp-research/slurk) server.

[Wordle](https://en.wikipedia.org/wiki/Wordle) is a popular word-guessing game. In its original form it is prompt-less and played by a single player. This bot offers a collaborative twist, with two players working together to guess the target word. Additionally, there is an image as a prompt, and the target word is explicitly or implicitly found in the image. The players can discuss as long as they want before entering their guess, but they must coordinate and input the exact same word at the same time. The players have 5 tries.

## Setting up and running the Wordle bot

### Setup

1. Install [Docker](https://docs.docker.com/get-docker/). You might also need the [jq package](https://stedolan.github.io/jq/download/) too.
2. Clone the [slurk](https://github.com/clp-research/slurk) repository.
3. Copy the [```wordle.js```](wordle.js) file to [```slurk/slurk/views/static/plugins```](https://github.com/clp-research/slurk/tree/master/slurk/views/static/plugins).
4. Before running the bot, several environmental variables would need to be generated and assigned. This process is detailed in the [documentation](https://clp-research.github.io/slurk/slurk_gettingstarted.html), which details both the general preparation and the [bot specific initialisations](https://clp-research.github.io/slurk/slurk_gettingstarted.html#chatting-with-a-bot). The bot also needs to have specific permissions, listed below this paragraph. The above permissions can be found in [this example permissions file](https://github.com/clp-research/slurk-bots/blob/master/wordle/data/wordle_bot_permissions.json) already.  
    ```
    {
        "api": true,
        "send_html_message": true,
        "send_privately": true,
        "send_command": true
    }
    ```
4. Make sure that the [slurk](https://github.com/clp-research/slurk) and slurk-bots repositories live next to each other on the same level.
5. Copy the content of the [```plugins```] directory to [```slurk/slurk/views/static/plugins```](https://github.com/clp-research/slurk/tree/master/slurk/views/static/plugins).
6. Navigate to the base directory of the slurk-bots repository and run the script to launch this bot, your command should look like this:  
 ```$ python start_bot.py wordle/ --users 2 --copy-plugins --dev --waiting-room-layout-dict wordle/data/waiting_room_layout.json```.  
 This script will build and run the docker images, it will initialise all the env variables with the right permissions and it will set everything up for testing locally on your computer. The bot will appear in your containers list as ```slurk/wordle```.

### Running and playing the bot

If you have everything already set up, you can run the bot using the following command (take notice of the right env variable names):    
```bash
docker run \
    --net="host" \
    -e BOT_TOKEN=$WORDLE_BOT_TOKEN \
    -e BOT_ID=$WORDLE_BOT \
    -e WAITING_ROOM=$WAITING_ROOM \
    -e TASK_ID=$TASK_ID \
    -e SLURK_PORT=5000 \
    -d slurk/wordle-bot
```

## Modifications and Game Variants
Under `lib/config.py` you find a number of global variables that define experiment settings as well as short descriptions of their effect on the experiment.

Word/image pairs should be specified in a tab separated file: ```data/image_data.tsv```. The components of a pair are separated by a tab in the order: word tab link-to-image.

The game can be played in different variants as specified in the configuration file:

- **same** (default): Both players see the same image.
- **one_blind**: Only one players sees the image. Who sees the image changes with every round.
- **different**: Each player sees a different image; both images are related to the word. This requires the image_data.tsv to have an additional column specifying a second image for every word. (The other two modes will work with this 3-column file as well.)
