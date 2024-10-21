## Echo Bot
This bot parrots user messages. If a private message is sent to the bot by a user, the bot will send it back to this individual user only. Other messages are sent back to the room from where they were received.

* `on_text_message`: triggered for messages containing text
* `on_image_message`: triggered for messages containing images


## Setting up and running

### Setup 

1. Install [Docker](https://docs.docker.com/get-docker/). You might also need the [jq package](https://stedolan.github.io/jq/download/) too. 
2. Clone the [slurk](https://github.com/clp-research/slurk) repository.
3. Before running the bot, several environmental variables would need to be generated and assigned. This process is detailed in the [documentation](https://clp-research.github.io/slurk/slurk_gettingstarted.html), which details both the general preparation and the [bot specific initialisations](https://clp-research.github.io/slurk/slurk_gettingstarted.html#chatting-with-a-bot). The bot also needs to have specific permissions, listed below this paragraph. The above permissions can be found in [this example permissions file](https://github.com/clp-research/slurk-bots/blob/master/echo/data/bot_permissions.json) already.  
    ```
    {
        "api": true,
        "send_message": true,
        "send_image": true,
        "send_privately": true
    }
    ```
 4. Make sure that the [slurk](https://github.com/clp-research/slurk) and slurk-bots repositories live next to each other on the same level.
 5. Navigate to the base directory of the slurk-bots repository and run the script to launch this bot, your command should look like this:  
 ```$ python start_bot.py echo/ --users 1 --tokens --dev```.  
 This script will build and run the docker images, it will initialise all the env variables with the right permissions and it will set everything up for testing locally on your computer. The bot will appear in your containers list as ```slurk/echo```.
    
### Running and playing the bot
If you have everything already set up, you can run the bot using the following command (take notice of the right env variable names):    
```bash
docker run \
    --net="host" \
    -e BOT_TOKEN=$THIS_BOT_TOKEN \
    -e BOT_ID=$THIS_BOT \
    -e TASK_ID=$TASK_ID \
    -e SLURK_PORT=5000 \
    -d slurk/echo-bot
```

To access the waiting rooms, you will need to input the saved tokes as well as any string as username. If you ran the setup script, there will be a token towards the end that will look something like this: `2f42a98e-0a29-43c2-9f94-97b38f25c30f`


## Echo Bot as a Blueprint  
Because of its simplicity, the Echo Bot can be used as a blueprint for writing your own bot. Once you have defined your Bot in `__main__.py` along with `data/user_permissions.json`, `data/bot_permissions.json` and `data/task_layout.json`, you can start your bot and test it.
