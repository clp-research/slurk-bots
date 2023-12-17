# -*- coding: utf-8 -*-
# University of Potsdam
"""Commandline interface."""

import argparse
import logging
import os

from .wordle_bot import WordleBot2


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = argparse.ArgumentParser(description="Run Wordle Bot.")

    # collect environment variables as defaults
    if "BOT_TOKEN" in os.environ:
        token = {"default": os.environ["BOT_TOKEN"]}
    else:
        token = {"required": True}
    if "BOT_ID" in os.environ:
        user = {"default": os.environ["BOT_ID"]}
    else:
        user = {"required": True}

    if "WAITING_ROOM" in os.environ:
        waiting_room = {"default": os.environ["WAITING_ROOM"]}
    else:
        waiting_room = {"required": True}

    parser.add_argument(
        "--waiting_room",
        type=int,
        help="room where users await their partner",
        **waiting_room
    )

    host = {"default": os.environ.get("SLURK_HOST", "http://localhost")}
    port = {"default": os.environ.get("SLURK_PORT")}
    task_id = {"default": os.environ.get("TASK_ID")}

    # register commandline arguments
    parser.add_argument("-t", "--token", help="token for logging in as bot", **token)
    parser.add_argument("-u", "--user", help="user id for the bot", **user)
    parser.add_argument(
        "-c", "--host", help="full URL (protocol, hostname) of chat server", **host
    )

    # versions:
    #  clue : a guesser gets a clue about the word before they start guesing
    #  standard: no clue is provided

    if "BOT_VERSION" in os.environ:
        bot_version = {"default": os.environ["BOT_VERSION"]}
    else:
        bot_version = {"required": True}

    parser.add_argument(
        "--bot_version",
        type=str,
        help="version of wordle game",
        **bot_version,
    )
    parser.add_argument("-p", "--port", type=int, help="port of chat server", **port)
    parser.add_argument("--task_id", type=int, help="task to join", **task_id)

    args = parser.parse_args()

    # create bot instance
    wordle_bot = WordleBot2(args.token, args.user,args.task_id, args.host, args.port)
    # wordle_bot.waiting_room = args.waiting_room
    wordle_bot.post_init(args.waiting_room, args.bot_version)

    # connect to chat server
    wordle_bot.run()
