import argparse
import configparser
import json
from pathlib import Path


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
            user_permissions_id, args.waiting_room_id, args.task_id
        )
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
        help="api address to your slurk server",
    )
    parser.add_argument(
        "--slurk-api-token",
        help="slurk token with api permissions",
        default="00000000-0000-0000-0000-000000000000",
    )
    parser.add_argument(
        "--credentials-from-file", help="read slurk host and api token from a json file"
    )
    parser.add_argument(
        "--waiting-room-id",
        type=int,
        help="room_id of an existing waiting room.",
        required=True,
    )
    parser.add_argument(
        "--task-id",
        type=int,
        help="task_id of an existing task",
        required=True,
    )

    args = parser.parse_args()

    # define some variables here
    SLURK_HOST = args.slurk_host
    SLURK_API = f"{args.slurk_host}/slurk/api"
    API_TOKEN = args.slurk_api_token

    if args.credentials_from_file:
        credentials_file = Path(args.credentials_from_file)
        if not credentials_file.exists():
            raise FileNotFoundError("Missing file with slurk credentials")

        config = configparser.ConfigParser()
        config.read(Path(args.credentials_from_file))
        config.sections()

        if any(config["SLURK CREDENTIALS"].get(i) is None for i in ["host", "token"]):
            raise ValueError("Invalid formatting for credentials file")

        sulrk_address = config.get("SLURK CREDENTIALS", "host")
        SLURK_HOST = sulrk_address
        SLURK_API = f"{sulrk_address}/slurk/api"
        API_TOKEN = config.get("SLURK CREDENTIALS", "token")

    # start bot
    main(args)
