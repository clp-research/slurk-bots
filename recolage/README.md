## RecolageBot
This bot loads pre-defined [GOLMI](https://github.com/clp-research/golmi) boards and show them to the users.
One of the users is the Instruction Giver (or Player) and has to describe the target piece to the Instruction Receiver (or Wizard) who then has to select the correct target.
There are 4 versions of this bot:
* no feedback: the users can not communicate with each other
* feedback: the IR can send a generic warning to the IG and both users are notified about the outcome of the task
* confirm selection: once the IR selects an object, the IG needs to confirm the selection
* gripper: the IR will select the target piece by moving a gripper on the GOLMI board, the gripper and its movements are broadcasted live to the IG.

## Setting up and running

### Setup 

1. Install [Docker](https://docs.docker.com/get-docker/). You might also need the [jq package](https://stedolan.github.io/jq/download/) too. 
2. Clone the [slurk](https://github.com/clp-research/slurk) repository.
3. Before running the bot, several environmental variables would need to be generated and assigned. This process is detailed in the [documentation](https://clp-research.github.io/slurk/slurk_gettingstarted.html), which details both the general preparation and the [bot specific initialisations](https://clp-research.github.io/slurk/slurk_gettingstarted.html#chatting-with-a-bot). The bot also needs to have specific permissions, listed below this paragraph. The above permissions can be found in [this example permissions file](https://github.com/clp-research/slurk-bots/blob/golmi/golmi/data/bot_permissions.json) already.  
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
6. Navigate to the base directory of this repository and run the script to launch this bot, your command should look like this:  
 ```$ python start_bot.py recolage --users 2 --extra-args recolage/args_feedback.json --copy-plugins --dev```.  
 This script will build and run the docker images, it will initialise all the env variables with the right permissions and it will set everything up for testing locally on your computer. The bot will appear in your containers list as ```slurk/recolage```.

### Running and playing the bot
A [GOLMI server](https://github.com/clp-research/golmi) is needed to run this bot. Make sure that golmi is on the `slurk` branch.

If you have everything already set up, you can run the bot using the following command (take notice of the right env variable names):    
```bash
docker run \
    --net="host" \
    -e BOT_TOKEN=$THIS_BOT_TOKEN \
    -e BOT_USER=$THIS_BOT \
    -e TASK_ID=$TASK_ID \
    -e WAITING_ROOM=$WAITING_ROOM \
    -e SLURK_PORT=5000 \
    -e GOLMI_SERVER=$GOLMI_SERVER \
    -e GOLMI_PASSWORD=$GOLMI_PASSWORD \
    -e VERSION=$BOT_VERSION \
    -d slurk/recolage
```

This bot has different versions, you can choose the one you want by selecting the according `args_{version}.json` with the `--extra-args path/to/args-file.json` option.
