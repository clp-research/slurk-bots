import argparse
import logging
import os

import requests
import socketio


LOG = logging.getLogger(__name__)


class ConciergeBot:
    sio = socketio.Client(logger=True)
    tasks = dict()

    def __init__(self, token, user, host, port, openvidu=False):
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
        :param openvidu: Whether slurk has an OpenVidu connection specified
            that is to be used.
        :type openvidu: bool
        """
        self.token = token
        self.user = user
        self.openvidu = openvidu
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
                    self.user_task_join(user, task, data["room"], self.openvidu)
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
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not task.ok:
            LOG.error(f"Could not get task: {task.status_code}")
            exit(2)
        LOG.debug("Got user task successfully.")
        return task.json()

    def get_user(self, user):
        response = requests.get(
            f"{self.uri}/users/{user}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not response.ok:
            LOG.error(
                f"Could not get user: {response.status_code}"
            )
            response.raise_for_status()
        return response.headers["ETag"]

    def create_room(self, layout_id, openvidu_session_id=None):
        """Create room for the task.

        :param layout_id: Unique key of layout object.
        :type layout_id: int
        """
        json = {"layout_id": layout_id}

        if openvidu_session_id:
            json["openvidu_session_id"] = openvidu_session_id

        room = requests.post(
            f"{self.uri}/rooms",
            headers={"Authorization": f"Bearer {self.token}"},
            json=json,
        )
        if not room.ok:
            LOG.error(f"Could not create task room: {room.status_code}")
            exit(3)
        LOG.debug("Created room successfully.")
        return room.json()

    def create_openvidu_session(self):
        """Create OpenVidu session for a room."""
        session = requests.post(
            f"{self.uri}/openvidu/sessions",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not session.ok:
            LOG.error(f"Could not create openvidu session: {session.status_code}")
            exit(3)
        LOG.debug("Created OpenVidu session successfully.")
        return session.json()

    def join_room(self, user_id, room_id):
        """Let user join task room.

        :param user_id: Identifier of user.
        :type user_id: int
        :param room_id: Identifier of room.
        :type room_id: int
        """
        response = requests.post(
            f"{self.uri}/users/{user_id}/rooms/{room_id}",
            headers={"Authorization": f"Bearer {self.token}"},
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
            headers={"Authorization": f"Bearer {self.token}", "If-Match": etag},
        )
        if not response.ok:
            LOG.error(f"Could not remove user from room: {response.status_code}")
            exit(5)
        LOG.debug("Removing user from room was successful.")

    def user_task_join(self, user, task, room, openvidu=False):
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
            session_id = None

            if openvidu:
                # create session
                session = self.create_openvidu_session()
                session_id = session["id"]
            new_room = self.create_room(task["layout_id"], session_id)
            # list cast necessary because the dictionary is actively altered
            # due to parallely received "leave" events
            for user_id, old_room_id in list(self.tasks[task_id].items()):
                etag = self.get_user(user_id)
                self.delete_room(user_id, old_room_id, etag)
                self.join_room(user_id, new_room["id"])
            del self.tasks[task_id]
            self.sio.emit("room_created", {"room": new_room["id"], "task": task_id})

            LOG.info(f"Created session {session_id}")

        else:
            self.sio.emit(
                "text",
                {
                    "message": f"### Hello, {user_name}!\n\n"
                    "I am looking for a partner for you, it might take "
                    "some time, so be patient, please...",
                    "receiver_id": user_id,
                    "room": room,
                    "html": True,
                },
                callback=self.message_callback,
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
    if "BOT_TOKEN" in os.environ:
        token = {"default": os.environ["BOT_TOKEN"]}
    else:
        token = {"required": True}
    if "BOT_ID" in os.environ:
        user = {"default": os.environ["BOT_ID"]}
    else:
        user = {"required": True}
    host = {"default": os.environ.get("SLURK_HOST", "http://localhost")}
    port = {"default": os.environ.get("SLURK_PORT")}
    openvidu = {"default": bool(os.environ.get('SLURK_OPENVIDU_URL'))}

    # register commandline arguments
    parser.add_argument(
        "-t", "--token", help="token for logging in as bot (see SERVURL/token)", **token
    )
    parser.add_argument("-u", "--user", help="user id for the bot", **user)
    parser.add_argument(
        "-c", "--host", help="full URL (protocol, hostname) of chat server", **host
    )
    parser.add_argument("-p", "--port", type=int, help="port of chat server", **port)
    parser.add_argument(
        "--openvidu", type=bool, help="specify if an OpenVidu connection exists", **openvidu
        )
    args = parser.parse_args()

    # create bot instance
    concierge_bot = ConciergeBot(args.token, args.user, args.host, args.port, args.openvidu)
    # connect to chat server
    concierge_bot.run()
