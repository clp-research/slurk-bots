### Chatbot

This bot template can be used to hook up slurk to a chatbot API.

The bot will handle administrative tasks and act as the interaction partner.

The template is set up for players to enter a common room.
As soon as a player has entered, the actual chatbot room will be created and
both the player and the bot will move there for the interaction to take place.

Players start the interaction with the `/ready` command and can end it with
the `/stop` command.

## Setting up and running

This bot is built on top of the template TaskBot (`slurk-bots/templates.py`)
and uses the ConciergeBot for managing entering players 
(`slurk-bots/concierge`).
You can start the docker setup locally by running `./chatbot/setup.sh` from 
the slurk-bots directory.

### Set up API access to the chatbot of your choice

### Setup

The bot also needs to have specific permissions, listed below this paragraph. The above permissions can be found in [this example permissions file](https://github.com/clp-research/slurk-bots/blob/master/dito/data/dito_bot_permissions.json) already.  
    ```
    {
        "api": true,
        "send_html_message": true,
        "send_privately": true
    }
    ```
