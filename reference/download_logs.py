"""
This script can be used to download slurk logs
 in jsonl format given a valid task_id
"""


import argparse
from datetime import datetime
import json
from pathlib import Path
import requests


def get_layout_id(task_id):
    layout = requests.get(f"{URL}/tasks/{task_id}").json()
    return layout["layout_id"]


def get_rooms(layout_id):
    task_rooms = requests.get(f"{URL}/rooms?layout_id={layout_id}").json()
    return set([i["id"] for i in task_rooms])


def main(args):
    layout_id = get_layout_id(args.task_id)
    rooms = get_rooms(layout_id)

    for room in rooms:
        data = requests.get(
            f"{URL}/logs?room_id={room}",
            headers={"Authorization": f"Bearer {args.token}"},
        ).json()
        events = sorted(data, key=lambda x: datetime.fromisoformat(x["date_created"]))

        # create output folder
        outputdir = Path(args.output_dir)
        outputdir.mkdir(exist_ok=True)

        with Path(f"{outputdir}/{room}_new.jsonl").open("w", encoding="utf-8") as ofile:
            for event in events:
                print(json.dumps(event), file=ofile)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task_id", type=int, required=True)
    parser.add_argument(
        "--slurk-host",
        default="http://127.0.0.1:5000",
        help="address to your slurk server",
    )
    parser.add_argument(
        "--token",
        help="slurk token with api permissions",
        default="00000000-0000-0000-0000-000000000000",
    )
    parser.add_argument(
        "--output-dir", help="directory where the logs will be saved", required=True
    )
    args = parser.parse_args()

    URL = f"{args.slurk_host}/slurk/api"
    main(args)
