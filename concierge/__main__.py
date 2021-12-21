import logging

import requests

from templates import Bot


class ConciergeBot(Bot):
    def __init__(self, token, user, host, port):
        """This bot lists users joining a designated
        waiting room and sends a group of users to a task room
        as soon as the minimal number of users needed for the
        task is reached.
        """
        super().__init__(token, user, host, port)
        self.tasks = dict()

    def register_callbacks(self):
        @self.sio.event
        def status(data):
            user = data["user"]
            task = self.get_user_task(user)
            if data["type"] == "join":
                if task:
                    self.user_task_join(user, task, data["room"])
            elif data["type"] == "leave":
                if task:
                    self.user_task_leave(user, task)

    def get_user_task(self, user):
        """Retrieve task assigned to user.

        :param user: Holds keys `id` and `name`.
        :type user: dict
        """
        task = requests.get(
            f'{self.uri}/users/{user["id"]}/task',
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.request_feedback(task, "ConciergeBot requests user task")
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
        self.request_feedback(room, "ConciergeBot creates task room")
        return room.json()

    def join_room(self, user_id, room_id):
        """Let user join task room.

        :param user_id: Identifier of user.
        :type user_id: int
        :param room_id: Identifier of room.
        :type room_id: int
        """
        response = requests.post(
            f"{self.uri}/users/{user_id}/rooms/{room_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.request_feedback(response, "ConciergeBot sends user to task room")
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
            headers={"Authorization": f"Bearer {self.token}",
                     "If-Match": etag}
        )
        self.request_feedback(response, "ConciergeBot removes user from waiting room")

    def user_task_join(self, user, task, room_id):
        """A connected user and their task are registered.

        Once the final user necessary to start a task
        has entered, all users for the task are moved to
        a dynamically created task room.

        :param user: Holds keys `id` and `name`.
        :type user: dict
        :param task: Holds keys `date_created`, `date_modified`, `id`,
            `layout_id`, `name` and `num_users`.
        :type task: dict
        :param room_id: Identifier of a room that the user joined.
        :type room_id: str
        """
        task_id = task["id"]
        user_id = user["id"]
        user_name = user["name"]
        # register task together with the user_id
        self.tasks.setdefault(task_id, {})[user_id] = room_id

        if len(self.tasks[task_id]) == task["num_users"]:
            new_room = self.create_room(task["layout_id"])
            # list cast necessary because the dictionary is actively altered
            # due to parallel received "leave" events
            for user_id, old_room_id in list(self.tasks[task_id].items()):
                etag = self.join_room(user_id, new_room["id"])
                self.delete_room(user_id, old_room_id, etag)
            del self.tasks[task_id]
            self.sio.emit("room_created", {"room": new_room["id"], "task": task_id})
        else:
            self.sio.emit(
                "text",
                {
                    "message":
                        f"### Hello, {user_name}!\n\n"
                        "I am looking for a partner for you, it might take "
                        "some time, so be patient, please...",
                    "receiver_id": user_id,
                    "room": room_id,
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
    parser = ConciergeBot.create_argparser()
    args = parser.parse_args()

    # create bot instance
    concierge_bot = ConciergeBot(args.token, args.user, args.host, args.port)
    # connect to chat server
    concierge_bot.run()
