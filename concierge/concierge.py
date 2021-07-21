import argparse
import logging
import os

import requests
import socketio


LOG = logging.getLogger(__name__)


class ConciergeBot:
    sio = socketio.Client(logger=True)
    tasks = dict()

    def __init__(self, token, user, host, port):
        """This bot lists users joining a designated
        waiting room and sends a group of users to a task room
        as soon as the minimal number of users needed for the
        task is reached.

        :param token: A uuid; a string following the same pattern
            as `0c45b30f-d049-43d1-b80d-e3c3a3ca22a0`
        :type token: str
        :param user: ID of a `User` object that was created with
        the token.
        :type user: int
        :param host: Full URL including protocol and hostname.
        :type host: str
        :param port: Port used by the slurk chat server.
        :type port: int
        """
        self.token = token
        self.user = user
        self.uri = host
        if port is not None:
            self.uri += f":{port}"
        self.uri += "/slurk/api"

        LOG.info(f"Running concierge bot on {self.uri} with token {self.token}")
        # register all event handlers
        self.register_callbacks()

    def run(self):
        # establish a connection to the server
        self.sio.connect(
            self.uri,
            headers={"Authorization": f"Bearer {self.token}", "user": self.user},
            namespaces="/",
        )
        # wait until the connection with the server ends
        self.sio.wait()

    def register_callbacks(self):
        @self.sio.event
        def status(data):
            if data["type"] == "join":
                user = data["user"]
                task = self.get_user_task(user)
                if task:
                    self.user_task_join(user, task, data["room"])
            elif data["type"] == "leave":
                user = data["user"]
                task = self.get_user_task(user)
                if task:
                    self.user_task_leave(user, task)

    @staticmethod
    def message_callback(success, error_msg=None):
        """Is passed as an optional argument to a server emit.

        Will be invoked after the server has processed the event,
        any values returned by the event handler will be passed
        as arguments.

        :param success: `True` if the message was successfully sent,
            else `False`.
        :type success: bool
        :param error_msg: Reason for an insuccessful message
            transmission. Defaults to None.
        :type status: str, optional
        """
        if not success:
            LOG.error(f"Could not send message: {error_msg}")
            exit(1)
        LOG.debug("Sent message successfully.")

    def get_user_task(self, user):
        """Retrieve task assigned to user.

        :param user: Holds keys `id` and `name`.
        :type user: dict
        """
        task = requests.get(
            f'{self.uri}/users/{user["id"]}/task',
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not task.ok:
            LOG.error(f"Could not get task: {task.status_code}")
            exit(2)
        LOG.debug("Got user task successfully.")
        return task.json()

    def create_room(self, layout_id):
        """Create room for the task.

        :param layout_id: Unique key of layout object.
        :type layout_id: int
        """
        room = requests.post(
            f"{self.uri}/rooms",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"layout_id": layout_id}
        )
        if not room.ok:
            LOG.error(f"Could not create task room: {room.status_code}")
            exit(3)
        LOG.debug("Created room successfully.")
        return room.json()

    def join_room(self, user_id, room_id):
        """Let user join task room.

        :param user_id: Identifier of user.
        :type user_id: int
        :param room_id: Identifier of room.
        :type room_id: int
        """
        response = requests.post(
            f"{self.uri}/users/{user_id}/rooms/{room_id}"
        )
        if not response.ok:
            LOG.error(f"Could not let user join room: {response.status_code}")
            exit(4)
        LOG.debug("Sending user to new room was successful.")
        return response.headers["ETag"]

    def delete_room(self, user_id, room_id, etag):
        """Remove user from (waiting) room.

        :param user_id: Identifier of user.
        :type user_id: int
        :param room_id: Identifier of room.
        :type room_id: int
        :param etag: Used for request validation.
        :type etag: str
        """
        response = requests.delete(
            f"{self.uri}/users/{user_id}/rooms/{room_id}",
            headers={"If-Match": etag}
        )
        if not response.ok:
            LOG.error(f"Could not remove user from room: {response.status_code}")
            exit(5)
        LOG.debug("Removing user from room was successful.")

    def user_task_join(self, user, task, room):
        """A connected user and their task are registered.

        Once the final user necessary to start a task
        has entered, all users for the task are moved to
        a dynamically created task room.

        :param user: Holds keys `id` and `name`.
        :type user: dict
        :param task: Holds keys `date_created`, `date_modified`, `id`,
            `layout_id`, `name` and `num_users`.
        :type task: dict
        :param room: Identifier of a room that the user joined.
        :type room: str
        """
        task_id = task["id"]
        user_id = user["id"]
        user_name = user["name"]
        # register task together with the user_id
        self.tasks.setdefault(task_id, {})[user_id] = room

        if len(self.tasks[task_id]) == task["num_users"]:
            new_room = self.create_room(task["layout_id"])
            # list cast necessary because the dictionary is actively altered
            # due to parallely received "leave" events
            for user_id, old_room_id in list(self.tasks[task_id].items()):
                etag = self.join_room(user_id, new_room["id"])
                self.delete_room(user_id, old_room_id, etag)
            del self.tasks[task_id]
            self.sio.emit("room_created", {"room": new_room["id"], "task": task_id})
        else:
            import time  # TODO: temporary solution
            time.sleep(2)
            self.sio.emit(
                "text",
                {
                    "message":
                        f"### Hello, {user_name}!\n\n"
                        "I am looking for a partner for you, it might take "
                        "some time, so be patient, please...",
                    "receiver_id": user_id,
                    "room": room,
                    "html": True
                },
                callback=self.message_callback
            )

    def user_task_leave(self, user, task):
        """The task entry of a disconnected user is removed.

        :param user: Holds keys `id` and `name`.
        :type user: dict
        :param task: Holds keys `date_created`, `date_modified`, `id`,
            `layout_id`, `name` and `num_users`.
        :type task: dict
        """
        task_id = task["id"]
        user_id = user["id"]
        if task_id in self.tasks and user_id in self.tasks[task_id]:
            del self.tasks[task["id"]][user["id"]]


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = argparse.ArgumentParser(description="Run Concierge Bot.")

    # collect environment variables as defaults
    if "SLURK_TOKEN" in os.environ:
        token = {"default": os.environ["SLURK_TOKEN"]}
    else:
        token = {"required": True}
    if "SLURK_USER" in os.environ:
        user = {"default": os.environ["SLURK_USER"]}
    else:
        user = {"required": True}
    host = {"default": os.environ.get("SLURK_HOST", "http://localhost")}
    port = {"default": os.environ.get("SLURK_PORT")}

    # register commandline arguments
    parser.add_argument(
        "-t", "--token", help="token for logging in as bot (see SERVURL/token)", **token
    )
    parser.add_argument("-u", "--user", help="user id for the bot", **user)
    parser.add_argument(
        "-c", "--host", help="full URL (protocol, hostname) of chat server", **host
    )
    parser.add_argument("-p", "--port", type=int, help="port of chat server", **port)
    args = parser.parse_args()

    # create bot instance
    concierge_bot = ConciergeBot(args.token, args.user, args.host, args.port)
    # connect to chat server
    concierge_bot.run()
