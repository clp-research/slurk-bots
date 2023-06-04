import argparse
import configparser
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
from time import sleep

import requests


def build_docker_image(path, name=None):
    # if a name is not provided use the name
    # of the directory with a  "-bot" ending
    bot_path = Path(path)
    if name is None:
        name = f"{Path(path)}-bot"

    subprocess.run(
        [
            "docker",
            "build",
            "--tag",
            f"slurk/{name}",
            "-f",
            f"{bot_path}/Dockerfile",
            ".",
        ]
    )


def create_room_layout(room_layout):
    response = requests.post(
        f"{SLURK_API}/layouts",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        json=room_layout,
    )

    if not response.ok:
        print(f"could not create room layout: {room_layout['title']}")
        response.raise_for_status()

    return response.json()["id"]


def create_room(room_layout):
    response = requests.post(
        f"{SLURK_API}/rooms",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        json={"layout_id": room_layout},
    )

    if not response.ok:
        print(f"could not create room: {room_layout['title']}")
        response.raise_for_status()

    return response.json()["id"]


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


def create_user(name, token):
    response = requests.post(
        f"{SLURK_API}/users",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        json={"name": name, "token_id": token},
    )

    if not response.ok:
        print(f"could not create user: {name}")
        response.raise_for_status()

    return response.json()["id"]


def find_task_layout_file(path):
    for filename in path.rglob("*.json"):
        if all(i in str(filename) for i in ["task", "layout"]):
            return filename

    raise FileNotFoundError(
        "Missing task layout file. Consider naming your layout file: task_layout.json"
    )


def find_bot_permissions_file(path):
    for filename in path.rglob("*.json"):
        if all(i in str(filename) for i in ["bot", "permissions"]):
            return filename

    raise FileNotFoundError(
        "Missing bot permissions file. Consider naming your layout file: bot_permissions.json"
    )


def find_user_permissions_file(path):
    for filename in path.rglob("*.json"):
        if all(i in str(filename) for i in ["user", "permissions"]):
            return filename

    raise FileNotFoundError(
        "Missing user permissions file. Consider naming your layout file: user_permissions.json"
    )


def create_task(name, num_users, layout_id):
    response = requests.post(
        f"{SLURK_API}/tasks",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        json={"name": name, "num_users": num_users, "layout_id": layout_id},
    )

    if not response.ok:
        print(f"could not create task: {name}")
        response.raise_for_status()

    return response.json()["id"]


def main(args):
    bot_base_path = Path(args.bot)

    if args.dev is True:
        if any([args.waiting_room_id, args.waiting_room_layout_id]):
            raise ValueError(
                "You provided a waiting room id or layout, you cannot also start a new slurk server"
            )

        if not Path("../slurk").exists():
            raise FileNotFoundError(
                "../slurk is missing, donwload it first: https://github.com/clp-research/slurk/"
                " and make sure that slurk and slurk-bots are in the same directory"
            )


        if args.copy_plugins is True:
            # plugins must be all placed in the plugin directory
            target_dir = Path("../slurk/slurk/views/static/plugins/")
            plugins_path = Path(f"{bot_base_path}/plugins")

            if not plugins_path.exists():
                raise FileNotFoundError("Your bot is missing a 'plugins' directory")

            for filename in plugins_path.iterdir():
                shutil.copy(filename, target_dir)

        # build image
        subprocess.run(
            ["docker", "build", "--tag", "slurk/server", "-f", "Dockerfile", "."],
            cwd=Path("../slurk"),
        )

        # run slurk server
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "-p",
                "5000:80",
                f"-e SLURK_SECRET_KEY={random.randint(0, 100000)}",
                "-e SLURK_DISABLE_ETAG=False",
                "-e FLASK_ENV=development",
                "slurk/server:latest",
            ]
        )

        sleep(1)

    # create a waiting room if not provided
    if args.waiting_room_id is None:
        # create a waiting_room_layout (or read from args)
        waiting_room_layout_dict_path = Path(args.waiting_room_layout_dict) 
        if not Path(waiting_room_layout_dict_path).exists():
            raise FileNotFoundError("Missing layout file for the waiting room")

        waiting_room_layout_dict = json.loads(
            Path(waiting_room_layout_dict_path).read_text(encoding="utf-8")
        )
        waiting_room_layout = args.waiting_room_layout_id or create_room_layout(
            waiting_room_layout_dict
        )

        # create a new waiting room
        waiting_room_id = create_room(waiting_room_layout)

        # create a concierge bot for this room
        concierge_name = f"concierge-bot-{bot_base_path}"

        concierge_bot_permissions_file = find_bot_permissions_file(Path("concierge"))
        concierge_permissions_dict = json.loads(
            concierge_bot_permissions_file.read_text(encoding="utf-8")
        )
        concierge_permissions = create_permissions(concierge_permissions_dict)
        concierge_bot_token = create_token(concierge_permissions, waiting_room_id)
        concierge_bot_user_id = create_user(concierge_name, concierge_bot_token)

        # start a concierge bot
        if "concierge" in args.bot:
            concierge_name = "concierge"
        
        build_docker_image("concierge", concierge_name)
        subprocess.run(
            [
                "docker",
                "run",
                "--restart",
                "unless-stopped",
                "--network",
                "host",
                "-d",
                f"-e BOT_TOKEN={concierge_bot_token}",
                f"-e BOT_USER={concierge_bot_user_id}",
                f"-e SLURK_HOST={args.slurk_host}",
                f"slurk/{concierge_name}",
            ]
        )

        if "concierge" in args.bot:
            print("---------------------------")
            print(f"waiting room id:\t{waiting_room_id}")
            print("---------------------------")
            return
    else:
        waiting_room_id = args.waiting_room_id

    # create task room
    # look for the task room layout (allow some options)
    task_room_layout_path = find_task_layout_file(bot_base_path)
    task_room_layout_dict = json.loads(task_room_layout_path.read_text(encoding="utf-8"))
    task_room_layout_id = create_room_layout(task_room_layout_dict)

    bot_name = args.bot_name or str(bot_base_path)
    task_id = create_task(
        f"{bot_name.capitalize()} Task", args.users, task_room_layout_id
    )
    task_bot_permissions_path = find_bot_permissions_file(bot_base_path)
    task_bot_permissions_dict = json.loads(task_bot_permissions_path.read_text(encoding="utf-8"))
    task_bot_permissions_id = create_permissions(task_bot_permissions_dict)
    task_bot_token = create_token(task_bot_permissions_id, waiting_room_id)
    task_bot_user_id = create_user(bot_name, task_bot_token)

    build_docker_image(args.bot, bot_name)
    docker_args = [
        "docker",
        "run",
        "--restart",
        "unless-stopped",
        "--network",
        "host",
        "-d",
        f"-e BOT_TOKEN={task_bot_token}",
        f"-e BOT_USER={task_bot_user_id}",
        f"-e TASK_ID={task_id}",
        f"-e WAITING_ROOM={waiting_room_id}",
        f"-e SLURK_HOST={args.slurk_host}",
    ]

    if args.extra_args is not None:
        extra_args_path = Path(args.extra_args)
        # make sure extra-args config file exists:
        if not extra_args_path.exists():
            raise FileNotFoundError("Extra argument file missing")

        # read config file
        extra_args = configparser.ConfigParser()
        extra_args.optionxform=str  # arg names should be case sensitive
        extra_args.read(extra_args_path)
        extra_args.sections()

        # make sure it has the right structure
        if dict(extra_args).get("ARGS") is None:
            raise ValueError("Invalid formatting for extra argument file")

        # collect arguments
        for key, value in extra_args["ARGS"].items():
            docker_args.append(f"-e {key}={value}")

    docker_args.append(f"slurk/{bot_name}")
    print(docker_args)
    subprocess.run(docker_args)

    print("---------------------------")
    print(f"waiting room id:\t{waiting_room_id}")
    print(f"task id:\t\t{task_id}")
    print("---------------------------")

    if any([args.tokens, args.dev]) is True:
        user_permissions_path = find_user_permissions_file(bot_base_path)
        user_permissions_dict = json.loads(user_permissions_path.read_text(encoding="utf-8"))

        for user in range(args.users):
            user_permissions_id = create_permissions(user_permissions_dict)
            user_token = create_token(user_permissions_id, waiting_room_id, task_id)
            print(
                f"Token: {user_token} | Link: {args.slurk_host}/login?name=user_{user}&token={user_token}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "bot",
        help="path to the directory containing your bot",
    )
    parser.add_argument(
        "--extra-args",
        help="path to a configuration file containing extra variable to pass as environment variables to the bot docker",
    )
    parser.add_argument(
        "--bot-name",
        help="the name of your bot. If omitted, the name of the directory will be used",
    )
    parser.add_argument(
        "--users",
        help="number of users for this task",
        required=all("concierge" not in arg for arg in sys.argv),
        type=int
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
        "--credentials-from-file",
        help="read slurk host and api token from a json file"
    )
    parser.add_argument(
        "--waiting-room-id",
        type=int,
        help="room_id of an existing waiting room. With this option will not create a new waiting room or a concierge bot",
    )
    parser.add_argument(
        "--waiting-room-layout-id",
        type=int,
        help="layout_id of an existing layout for a waiting room.",
    )
    parser.add_argument(
        "--waiting-room-layout-dict",
        default="concierge/waiting_room_layout.json",
        help="path to a json file containing a layout for a waiting room",
    )
    parser.add_argument(
        "--tokens",
        action="store_true",
        help="generate and print tokens to test your bot",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="start a local slurk server for development",
    )
    parser.add_argument(
        "--copy-plugins",
        help="copy all the files in the plugins directory to slurk's plugins before starting the slurk server",
        action="store_true"
    )
    args = parser.parse_args()

    # define some variables here
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
        SLURK_API = f"{sulrk_address}/slurk/api"
        API_TOKEN = config.get("SLURK CREDENTIALS", "token")

    # start bot
    main(args)
