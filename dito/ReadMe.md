### DiTo Bot: Let's Spot the **Di**fference - **To**gether!
The setting is that agent A sees a picture, and separately, agent B also sees a picture; the task for the agents then is to determine, via exchanging messages, whether they are looking at the same picture or not.

This task can be divided into the following task phases:
1. Waiting for both players to get ready.
2. Presenting each of the two players one out of a pair of pictures.
3. Let both players discuss.
4. Collect their decision on whether the pictures are different. In one task variant one may also require them to provide a description of the suspected difference.


For this purpose the following commands are defined to manage the transition between task phases:
+ */ready* : Both players have to send this command in order to move from phase 1 to phase 2
+ */difference* or */done* : Indicates that the players think they have come to a conclusion. */difference* requires an additional description of the difference.

## Setting up and running

### Setup 

1. Install [Docker](https://docs.docker.com/get-docker/). You might also need the [jq package](https://stedolan.github.io/jq/download/) too. 
2. Clone the [slurk](https://github.com/clp-research/slurk) repository.
3. Before running the bot, several environmental variables would need to be generated and assigned. This process is detailed in the [documentation](https://clp-research.github.io/slurk/slurk_gettingstarted.html), which details both the general preparation and the [bot specific initialisations](https://clp-research.github.io/slurk/slurk_gettingstarted.html#chatting-with-a-bot). The bot also needs to have specific permissions, listed below this paragraph. The above permissions can be found in [this example permissions file](https://github.com/clp-research/slurk-bots/blob/master/dito/data/dito_bot_permissions.json) already.  
    ```
    {
        "api": true,
        "send_html_message": true,
        "send_privately": true
    }
    ```
    **To skip all this setup above, you could run a [setup script](https://github.com/clp-research/slurk-bots/blob/master/dito/scripts/setup.sh).** 
    1. Make sure that the [slurk](https://github.com/clp-research/slurk) and slurk-bots repositories live next to each other on the same level.
    2. Navigate to the base directory of this repository and run the script to launch this bot, your command should look like ```bash dito/scripts/setup.sh``` 
    This script will build and run the docker images, it will initialise all the env variables with the right permissions and it will set up two bots that can talk to each other locally on your computer. The bot will appear in your containers list as ```slurk/dito-bot```. At the end of the run there will be two tokens printed in the shell that you will need to paste to access the waiting rooms. 
4. Save the generated tokens!

Note: Every time a new terminal session is started, the env variables will need to be set up again. You can just run the script again. 
    
### Running and playing the bot

If you have everything already set up, you can run the bot using the following command (take notice of the right env variable names):    
```bash
docker run -e SLURK_TOKEN=$DITO_BOT_TOKEN -e SLURK_USER=$DITO_BOT -e SLURK_WAITING_ROOM=$WAITING_ROOM -e DITO_TASK_ID=$TASK_ID -e SLURK_PORT=5000 --net="host" slurk/dito-bot &
```

To access the waiting rooms, you will need to input the saved tokes as well as any string as username. If you ran the setup script, there will be two tokens towards the end that will look something like below.
```
2f42a98e-0a29-43c2-9f94-97b38f25c30f
4cf0a403-c8d4-48fa-a7b0-b8ea7d52a364
```


#### Modifications
Under `lib/config.py` you find a number of global variables that define experiment settings as well as short descriptions of their effect on the experiment.

Image pairs for the task should be specified one pair per line
in the `image_data.csv`. The components of a pair are separated by
a comma followed by no whitespace.


#### Versions
A variant of this bot compatible with slurk v2 can be accessed under the name `cola` in branch `2.0.0`. This older version comes with an AMT connector part.

