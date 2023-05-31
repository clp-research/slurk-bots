## Click Bot

This bot demonstrates how to use the functionality provided by the `mouse-tracking` script.
After being moved to the task room the user is shown a button that they can use to start the game.
While the game is running an image is displayed on the right side of the page. This image contains different objects that are described to the user one at a time. The user will only hear each audio once. They then have to click on the described object. They may also choose to skip this item by clicking the button at the top of the page. If the user has answered correctly this same button will also bring them to the next item.

To run the bot, you can run a command in a similar fashion as:
```bash
docker run -e SLURK_TOKEN=ad6f2c73-95c3-478f-977f-bc25edcd8c5e -e SLURK_USER=170 -e CLICK_DATA="test_items/shape-colors.json" -e CLICK_TASK_ID=2 -e SLURK_PORT=5000 --net="host" slurk/click-bot
```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api` and `send_message`
A user in this task has to be given the rights: `send_command`
Please refer to [the documentation](https://clp-research.github.io/slurk/slurk_multibots.html) for more detailed information.


## Setting up and running

### Setup 

1. Install [Docker](https://docs.docker.com/get-docker/). You might also need the [jq package](https://stedolan.github.io/jq/download/) too. 
2. Clone the [slurk](https://github.com/clp-research/slurk) repository.
3. Before running the bot, several environmental variables would need to be generated and assigned. This process is detailed in the [documentation](https://clp-research.github.io/slurk/slurk_gettingstarted.html), which details both the general preparation and the [bot specific initialisations](https://clp-research.github.io/slurk/slurk_gettingstarted.html#chatting-with-a-bot). The bot also needs to have specific permissions, listed below this paragraph. The above permissions can be found in [this example permissions file](https://github.com/clp-research/slurk-bots/blob/master/clickbot/click_bot_permissions.json) already.  
    ```
    {
        "api": true,
        "send_message": true
    }
    ```
 4. Make sure that the [slurk](https://github.com/clp-research/slurk) and slurk-bots repositories live next to each other on the same level.
 5. Navigate to the base directory of this repository and run the script to launch this bot, your command should look like this:  
 ```$ python start_bot.py clickbot/ --users 1 --tokens --dev --extra-args clickbot/extra-args.json```.  
 This script will build and run the docker images, it will initialise all the env variables with the right permissions and it will set up two bots that can talk to each other locally on your computer. The bot will appear in your containers list as ```slurk/clickbot```.

Note: Every time a new terminal session is started, the env variables will need to be set up again. You can just run the script again. 
    
### Running and playing the bot

If you have everything already set up, you can run the bot using the following command (take notice of the right env variable names):    
```bash
docker run \
    --net="host" \
    -e BOT_TOKEN=$CLICK_BOT_TOKEN \
    -e BOT_USER=$CLICK_BOT \
    -e CLICK_DATA="test_items/shape-colors.json" \
    -e TASK_ID=$TASK_ID \
    -e SLURK_PORT=5000 \
    -d slurk/clickbot
```

To access the waiting rooms, you will need to input the saved tokes as well as any string as username. If you ran the setup script, there will be a token towards the end that will look something like this: `2f42a98e-0a29-43c2-9f94-97b38f25c30f`