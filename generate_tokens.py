import argparse
import configparser
import json
from pathlib import Path
import sys

import randomname
import requests


def create_permissions(permissions):
    response = requests.post(
        f"{SLURK_API}/permissions",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        json=permissions,
    )

    if not response.ok:
        print("could not create permissions")
        response.raise_for_status()

    return response.json()["id"]


def create_token(permissions, room_id, task_id=None):
    response = requests.post(
        f"{SLURK_API}/tokens",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        json={
            "permissions_id": permissions,
            "room_id": room_id,
            "registrations_left": 1,
            "task_id": task_id,
        },
    )

    if not response.ok:
        print("could not create token")
        response.raise_for_status()

    return response.json()["id"]


def main(args):
    if args.user_permissions is None:
        user_permissions_dict = {"send_message": True, "send_command": True}

    else:
        user_permissions_dict = json.loads(
            Path(args.user_permissions).read_text(encoding="utf-8")
        )

    for user in range(args.n_tokens):
        user_permissions_id = create_permissions(user_permissions_dict)
        user_token = create_token(
            user_permissions_id, WAITING_ROOM_ID, TASK_ID
        )

        if args.complete_links is True:
            print(f"{SLURK_HOST}/login?name={randomname.get_name()}&token={user_token}")
        else:
            print(user_token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--user-permissions",
        help="path to the file containing the user permissions",
    )
    parser.add_argument(
        "--n-tokens",
        help="number of tokens to generate",
        required=True,
        type=int,
    )
    parser.add_argument(
        "--slurk-host",
        default="http://127.0.0.1:5000",
        help="address to your slurk server",
    )
    parser.add_argument(
        "--slurk-api-token",
        help="slurk token with api permissions",
        default="00000000-0000-0000-0000-000000000000",
    )
    parser.add_argument(
        "--waiting-room-id",
        type=int,
        help="room_id of an existing waiting room.",
        required="--config-file" not in sys.argv,
    )
    parser.add_argument(
        "--task-id",
        type=int,
        help="task_id of an existing task",
        required="--config-file" not in sys.argv,
    )
    parser.add_argument(
        "--complete-links",
        action="store_true",
        help="The script will print out complete links with random names instead of tokens alone"
    )
    parser.add_argument(
        "--config-file",
        help="read slurk and bot parameters from a configuration file"
        
    )

    args = parser.parse_args()

    # define some variables here
    SLURK_HOST = args.slurk_host
    SLURK_API = f"{args.slurk_host}/slurk/api"
    API_TOKEN = args.slurk_api_token

    TASK_ID = args.task_id
    WAITING_ROOM_ID = args.waiting_room_id

    if args.config_file:
        config_file = Path(args.config_file)
        if not config_file.exists():
            raise FileNotFoundError("Missing configuration file with slurk credentials")

        config = configparser.ConfigParser()
        config.read(Path(args.config_file))
        config.sections()

        if any(config["SLURK"].get(i) is None for i in ["host", "token"]):
            raise ValueError("Config file is missing slurk entries")

        if any(config["BOT"].get(i) is None for i in ["task_id", "waiting_room_id"]):
            raise ValueError("Config file is missing slurk entries")

        slurk_address = config.get("SLURK", "host")
        SLURK_HOST = slurk_address
        SLURK_API = f"{slurk_address}/slurk/api"
        API_TOKEN = config.get("SLURK", "token")

        TASK_ID = int(config.get("BOT", "task_id"))
        WAITING_ROOM_ID = int(config.get("BOT", "waiting_room_id"))

    # start bot
    main(args)
