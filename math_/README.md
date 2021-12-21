## Math Bot

This is a bot that moderates a simple math question and answer session between two players.
* `on_command`: provides interface for users to create and answer math questions

**Commands**  
* `/question` set a new math question, overriding any unanswered one
* `/answer` provide an answer to a question 

**Allowed Operators**  
Mathematical expressions may only contain a limited set of operators.

+ negative numbers e.g. `--4` -> `4`
+ subtract two expressions e.g. `1 - 5` -> `-4` |
+ add two expressions `6 + 7` -> `13` |
+ multiply two expressions `5 * 7` -> `35` |

**Run with docker (recommended)**
The bot can be run with a command that follows the pattern:
```bash
docker run -e SLURK_TOKEN=79d0ea16-d724-463d-9567-1500f716efed -e SLURK_USER=1 -e SLURK_PORT=5000 MATH_TASK_ID=1 --net="host" slurk/math-bot
```

**Run without docker**
Without docker, bots need to be started from the *slurk-bots* repository as follows:
```bash
python -m math_ --token 79d0ea16-d724-463d-9567-1500f716efed --user 1 --port 5000 --task 1
```

The token has to be linked to a permissions entry that gives the bot at least the following rights: `api`, `send_message`, `send_privately`.
Users assigned to this task need at least the rights: `send_command`
Please refer to <https://clp-research.github.io/slurk/slurk_multibots.html> for more detailed information.
