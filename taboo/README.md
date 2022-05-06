## Taboo Bot

This bot manages a game of taboo in which participants have to guess a word that another is trying to explain. The explaining participants sees the target word and a number of words she cannot use while explaining. The bot keeps track of the score and intervenes in case a forbidden word was used.

The bot can be run with a command that follows the pattern:
```bash
docker run -e SLURK_TOKEN=c8469175-8e34-4c69-a2c7-472edce424b3 -e SLURK_USER=1 -e SLURK_PORT=5000 -e TASK_ID=1 -e DATA=taboo_words.json --net="host" slurk/taboo-bot
```

The script `setup.sh` runs the server and bots locally. It must be run from the slurk/ directory, assuming that slurk/ and slurk-bots/ have the same parent directory.

The token needs to have at least the permissions `api`, `send_privately`, `send_message`. Please refer to <https://clp-research.github.io/slurk/slurk_multibots.html> for more detailed information.

# Prerequisites

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
wget https://github.com/Kovah/Taboo-Data/blob/main/src/data/en/food.json
```
