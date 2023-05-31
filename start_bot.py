import argparse
import json
import random
from time import sleep
import subprocess
from pathlib import Path
import sys
import shutil

import requests


def build_docker_image(path, name=None):
    # if a name is not proved use the name
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

    print(
        "no task layout file found. Consider naming your layout file: task_layout.json"
    )
    return None


def find_bot_permissions_file(path):
    for filename in path.rglob("*.json"):
        if all(i in str(filename) for i in ["bot", "permissions"]):
            return filename

    print(
        "no bot permissions file found. Consider naming your layout file: bot_permissions.json"
    )
    return None


def find_user_permissions_file(path):
    for filename in path.rglob("*.json"):
        if all(i in str(filename) for i in ["user", "permissions"]):
            return filename

    print(
        "no user permissions file found. Consider naming your layout file: user_permissions.json"
    )
    return None


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
            print("You provided a waiting room id or layout, cannot also start slurk server")
            return
        if not Path("../slurk").exists():
            print(
                "slurk is missing, donwload it first: https://github.com/clp-research/slurk/"
            )
            return

        if args.copy_plugins is True:
            # plugins must be all placed in the plugin directory
            target_dir = Path("../slurk/slurk/views/static/plugins/")
            plugins_path = Path(f"{bot_base_path}/plugins")

            if not plugins_path.exists():
                print("Your bot is missing a 'plugins' directory")
                return

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
            print("could not find the layout file for the waiting room")
            return

        waiting_room_layout_dict = json.loads(
            Path(waiting_room_layout_dict_path).read_text()
        )
        waiting_room_layout = args.waiting_room_layout_id or create_room_layout(
            waiting_room_layout_dict
        )

        # create a new waiting room
        waiting_room_id = create_room(waiting_room_layout)

        # create a concierge bot for this room
        concierge_name = f"concierge-bot-{bot_base_path}"

        concierge_permissions_dict = json.loads(
            Path("concierge/concierge_bot_permissions.json").read_text()
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
    if task_room_layout_path is None:
        return

    task_room_layout_dict = json.loads(task_room_layout_path.read_text())
    task_room_layout_id = create_room_layout(task_room_layout_dict)

    bot_name = args.bot_name or str(bot_base_path)
    task_id = create_task(
        f"{bot_name.capitalize()} Task", args.users, task_room_layout_id
    )
    task_bot_permissions_path = find_bot_permissions_file(bot_base_path)
    if task_bot_permissions_path is None:
        return

    task_bot_permissions_dict = json.loads(task_bot_permissions_path.read_text())
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
        extra_args_list = list()
        extra_args = json.loads(Path(args.extra_args).read_text())
        for key, value in extra_args.items():
            extra_args_list.append(f"-e {key}={value}")

        docker_args.extend(extra_args_list)

    docker_args.append(f"slurk/{bot_name}")
    subprocess.run(docker_args)

    print("---------------------------")
    print(f"waiting room id:\t{waiting_room_id}")
    print(f"task id:\t\t{task_id}")
    print("---------------------------")

    if any([args.tokens, args.dev]) is True:
        user_permissions_path = find_user_permissions_file(bot_base_path)
        if user_permissions_path is None:
            return

        user_permissions_dict = json.loads(user_permissions_path.read_text())

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
        help="path to a json file containing extra variable to pass as environment variables to the bot docker",
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

    # start bot
    main(args)
