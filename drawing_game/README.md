## Drawing Game Bot

This bot manages a drawing game in which one participant must describe to another a 5x5 grid which contains a certain letter in certain positions. Player B needs to draw and return a grid according to the instructions given by player A in each turn. Once player A is done describing the grid they must say 'DONE' and the target and drawn grid will be compared against each other. 

## Setting up and running the Drawing Game bot

### Setup

1. Install [Docker](https://docs.docker.com/get-docker/). You might also need the [jq package](https://stedolan.github.io/jq/download/) too.
2. Clone the [slurk](https://github.com/clp-research/slurk) repository.
3. Before running the bot, several environmental variables would need to be generated and assigned. This process is explained in the [documentation](https://clp-research.github.io/slurk/slurk_gettingstarted.html), which details both the general preparation and the [bot specific initialisations](https://clp-research.github.io/slurk/slurk_gettingstarted.html#chatting-with-a-bot). The bot also needs to have specific permissions, listed below this paragraph. The above permissions can be found in [this example permissions file](https://github.com/sanchezpaez/slurk-bots/blob/sandra/drawing_game/data/bot_permissions.json) already.
    ```
    {
        "api": true,
        "send_html_message": true,
        "send_privately": true,
        "send_command": true
    }
    ```
4. Make sure that the [slurk](https://github.com/clp-research/slurk) and slurk-bots repositories live next to each other on the same level.
5. Navigate to the base directory of the slurk-bots repository and run the script to launch this bot, your command should look like this:
 ```$ python start_bot.py drawing_game --users 2 --copy-plugins --dev --waiting-room-layout-dict drawing_game/data/waiting_room_layout.json```.
 This script will build and run the docker images, it will initialise all the env variables with the right permissions and it will set everything up for testing locally on your computer. The bot will appear in your containers list as ```slurk/taboo```.

### Running and playing the bot

Game data – a list of grids to draw and match – is supplied via a json file that has the following pattern:


```json
{
    "low_en": [
        {
            "target_word": "klein",
            "related_word": [
                "small",
                "little",
                "short"
            ]
        },
        {
            "target_word": "atmospheric",
            "related_word": [
                "atmosphere",
                "ambient",
                "evocative"
            ],
        },
  ...
}
```
