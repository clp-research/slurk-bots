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
    "experiments": [
        {
            "name": "compact_grids",
            "game_instances": [
                {
                    "game_id": 0,
                    "player_1_prompt_header": "Let us play a game. The goal is to fill an empty grid that looks like this:\n\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\nA filled grid below is 5 by 5 and can look like this:\n\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 E \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\nX X X X X\n\nI want you to describe this grid to me, step by step. You don't need to describe the empty squares, which are denoted with \"\u25a2\". Only describe the location of letters in the grid. Then you wait for me to say \"What is your next instruction?\", and then you continue with the next step. Take the size of the grid into consideration while giving instructions. When you have described everything, you say \"DONE\".\n\nFor the filled grid above, here are the example steps.\n\nWhat is your next instruction?\nInstruction: Put an E in second row third column\n\nWhat is your next instruction?\nInstruction: Fill the last row with X\n\nWhat is your next instruction?\nInstruction: DONE\n\nAnother example with the following 5 by 5 grid:\n\nW \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 W \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 W \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 W \u25a2\nZ \u25a2 \u25a2 \u25a2 W\n\nWhat is your next instruction?\nInstruction: Put an W in five cells diagonally starting from top left going to bottom right\n\nWhat is your next instruction?\nInstruction: Put Z in the last row first column\n\nWhat is your next instruction?\nInstruction: DONE\n\nOk. Please do this for the following example, which is a 5 by 5 grid.",
                    "player_2_prompt_header": "Let us draw something together. There is an empty grid with a size 5 by 5, like so:\n\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\nI will give you instructions like \"put an X in the top left\", and you return the grid by applying the given instruction, like so:\n\nInstruction: put an X in the top left\n\nX \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\u25a2 \u25a2 \u25a2 \u25a2 \u25a2\n\nOr for another instruction such as \"fill the fifth column with T\", you return the updated grid by applying the given instruction in all places that the command corresponds to, like so:\n\nInstruction: fill the fifth column with T\n\nX \u25a2 \u25a2 \u25a2 T\n\u25a2 \u25a2 \u25a2 \u25a2 T\n\u25a2 \u25a2 \u25a2 \u25a2 T\n\u25a2 \u25a2 \u25a2 \u25a2 T\n\u25a2 \u25a2 \u25a2 \u25a2 T\n\nOr for another instruction such as \"fill the fourth column second row with P\", you return the updated grid by applying the given instruction in all places that the command corresponds to, like so:\n\nInstruction: fill the fourth column second row with P\n\nX \u25a2 \u25a2 \u25a2 T\n\u25a2 \u25a2 \u25a2 P T\n\u25a2 \u25a2 \u25a2 \u25a2 T\n\u25a2 \u25a2 \u25a2 \u25a2 T\n\u25a2 \u25a2 \u25a2 \u25a2 T\n\nNow create an empty grid with a size 5 by 5 and execute the following commands at each step. Once you execute the command, return only the grid and exclude all other text from the output.",
                    "player_1_question": "What is your next instruction?",
                    "grid_dimension": 5,
                    "number_of_letters": 0,
                    "fill_row": false,
                    "fill_column": false,
                    "target_grid": "B \u25a2 \u25a2 \u25a2 \u25a2\nB \u25a2 \u25a2 \u25a2 \u25a2\nB \u25a2 \u25a2 \u25a2 \u25a2\nB \u25a2 \u25a2 \u25a2 \u25a2\nB B B B B"
                },
          ...
     ...
}
```
