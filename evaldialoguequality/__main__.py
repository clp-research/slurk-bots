import logging
from threading import Timer
from time import sleep
import requests

from templates import TaskBot
from .dataloader import Dataloader


TIMEOUT_TIMER = 60  # minutes
COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
NEXT_DIALOGUE_COLOR = "Blue"
ERROR_DIALOGUE_COLOR = "Red"


class RoomTimer:
    def __init__(self, function, room_id):
        self.function = function
        self.room_id = room_id
        self.start_timer()

    def start_timer(self):
        self.timer = Timer(
            TIMEOUT_TIMER*60,
            self.function,
            args=[self.room_id]
        )
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        logging.debug("reset timer")

    def cancel(self):
        self.timer.cancel()


class EvalDlgQuality(TaskBot):
    timers_per_room = dict()

    def on_task_room_creation(self, data):
        logging.debug(data)
        room_id = data["room"]
        user_id = data['users'][0]['id']
        task_id = data["task"]


        if task_id is not None and task_id == self.task_id:
            self.timers_per_room[room_id] = RoomTimer(
                self.close_room, room_id
            )
            #Set the room to read only
            logging.debug(f"Setting the room to read_only, room_id = {room_id}, user_id = {user_id}")
            self.room_to_read_only(room_id, False)

            # move the chat | task area divider
            self.modify_layout(room_id)
            sleep(0.5)

            self.dataloader = Dataloader()
            #Show the welcome message
            self.showwelcomemessage(room_id, user_id)
            logging.debug(f"Done with welcome, calling load_dialogues")
            self.load_dialogues(room_id, user_id)
        else:
            logging.debug(f"Task ID {task_id} does not match the bot's task ID {self.task_id}. Ignoring room creation.")

    def close_room(self, room_id):
        self.room_to_read_only(room_id, True)
        self.timers_per_room.pop(room_id)

    def modify_layout(self, room_id, receiver_id=None):
        base_json = {"receiver_id": receiver_id} if receiver_id is not None else {}

        # Adjust height value for title bar adjustments- handled in both the first and third API calls
        titlebar_height = "height: 45px"
        titlebar_width_height = "width:30%; top: 45px"

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/header",
            headers={"Authorization": f"Bearer {self.token}"},
            # json={"attribute": "style", "value": f"height: 40px", **base_json},
            json={"attribute": "style", "value": titlebar_height, **base_json},
        )

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/sidebar",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "attribute": "style",
                #"value": f"height: 90%; width:70%; top: 40px",
                #with 90% height, scrolling action (up, down) is not working
                "value": f"height: 100%; width:70%; top: 40px",
                **base_json,
            },
        )

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/content",
            headers={"Authorization": f"Bearer {self.token}"},
            # json={"attribute": "style", "value": f"width:30%; top: 40px", **base_json},
            json={"attribute": "style", "value": titlebar_width_height, **base_json},
        )        

    def showwelcomemessage(self, room_id, user_id):
        """Show welcome message."""
        logging.debug(f"Inside showwelcomemessage, room_id = {room_id}, user_id = {user_id}")
        welcome_message = "On the right, you will find two dialogues. Your task is to select the dialogue<br>that feels more natural and conversational to you.<br><br>Please review both dialogues carefully and choose the one you believe is more natural.<br>Once you’ve made your selection, click the Next button to proceed.<br><br>Note: After clicking Next, you will not be able to return to the previous dialogues.<br>Make sure you are confident in your choice before proceeding. <br><br>"
        #Downloaded the image from this site: https://apps.timwhitlock.info/emoji/tables/unicode
        #Emoji: SCROLL, U+1F4DC
        task_message = "The dialogues are on your right ⏩<br>"
        self.sio.emit(
            "text",
            {
                "room": room_id,
                "message": COLOR_MESSAGE.format(
                    color=STANDARD_COLOR,
                    message=welcome_message+task_message,
                ),
                "receiver_id": user_id,
                "html": True,
            },
            callback=self.message_callback,
        )    

    def load_dialogues(self, room_id, user_id):
        logging.debug(f"Inside load_dialogues, room_id = {room_id}, user_id = {user_id}")

        dialogue_id, dialogue = self.dataloader.get_next_dialogue()
        self.current_dialogue_id = dialogue_id
        self.current_dialogue = dialogue

        if dialogue_id is None:
            logging.debug("No more dialogues available.")
            self.sio.emit(
                "message_command",
                {
                    "command": {"event": "clear_dialogue",
                                "message": None},
                    "room": room_id,
                    "receiver_id": user_id,
                },
            )              
            self.sio.emit(
                "text",
                {
                    "room": room_id,
                    "message": COLOR_MESSAGE.format(
                        color=STANDARD_COLOR,
                        message="Thank you for your time. The task is now complete. You may close this window.",
                    ),
                    "receiver_id": user_id,
                    "html": True,
                },
                callback=self.message_callback,
            ) 
            self.close_room(room_id)
            return
        
        logging.debug(f"Loaded dialogue: {dialogue_id}")
        logging.debug(f"Sending dialogue to room {room_id}")
        self.sio.emit(
            "message_command",
            {
                "command": {"event": "set_dialogue",
                             "message": {"dialogue_1": dialogue['left'], 
                                         "dialogue_2": dialogue['right']}},
                "room": room_id,
                "receiver_id": user_id,
            },
        )        



    def room_to_read_only(self, room_id, remove_user):
        """Set room to read only."""

        if not remove_user:
            # set room to read-only
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/attribute/id/text",
                json={"attribute": "readonly", "value": "True"},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                logging.error(f"Could not set room to read_only: {response.status_code}")
                response.raise_for_status()

            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/attribute/id/text",
                json={"attribute": "placeholder", "value": "This room is read-only"},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                logging.error(f"Could not set room to read_only: {response.status_code}")
                response.raise_for_status()

        else:
            response = requests.get(
                f"{self.uri}/rooms/{room_id}/users",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                logging.error(f"Could not get user: {response.status_code}")
                return            

            users = response.json()
            for user in users:
                if user["id"] != self.user:
                    response = requests.get(
                        f"{self.uri}/users/{user['id']}",
                        headers={"Authorization": f"Bearer {self.token}"},
                    )
                    if not response.ok:
                        logging.error(f"Could not get user: {response.status_code}")
                        response.raise_for_status()
                    etag = response.headers["ETag"]

                    response = requests.delete(
                        f"{self.uri}/users/{user['id']}/rooms/{room_id}",
                        headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
                    )
                    if not response.ok:
                        logging.error(
                            f"Could not remove user from task room: {response.status_code}"
                        )
                        response.raise_for_status()
                    logging.debug("Removing user from task room was successful.")




    def register_callbacks(self):
        @self.sio.event
        def text_message(data):
            if self.user == data["user"]["id"]:
                return
            else:
                room_id = data["room"]
                timer = self.timers_per_room.get(room_id)
                if timer is not None:
                    timer.reset()

            logging.debug(f"I got a message, let's send it back!: {data}")

            options = {}
            if data["private"]:
                logging.debug("It was actually a private message o.O")
                options["receiver_id"] = data["user"]["id"]

            message = data["message"]
            if message.lower() == "hello":
                message = "World!"
            elif message.lower() == "ping":
                message = "Pong!"

            self.sio.emit(
                "text",
                {
                    "room": data["room"],
                    "message": message,
                    **options
                },
                callback=self.message_callback,
            )

        @self.sio.event
        def image_message(data):
            if self.user == data["user"]["id"]:
                return
            else:
                room_id = data["room"]
                timer = self.timers_per_room.get(room_id)
                if timer is not None:
                    timer.reset()

            logging.debug(f"I got an image, let's send it back!: {data}")

            options = {}
            if data["private"]:
                logging.debug("It was actually a private image o.O")
                options["receiver_id"] = data["user"]["id"]

            self.sio.emit(
                "image",
                {
                    "room": data["room"],
                    "url": data["url"],
                    "width": data["width"],
                    "height": data["height"],
                    **options,
                },
                callback=self.message_callback,
            )

        @self.sio.event
        def command(data):
            """Parse frontend commands."""

            logging.debug(f"Received a front end command: {data}")

            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process commands from itself
            if user_id == self.user:
                logging.debug(f"user_id == self.user, returning")
                return
            
            if isinstance(data["command"], dict):
                # commands received from the frontend
                event = data["command"]["event"]
                logging.debug(f"Received command: data: {data['command']}")
                if event == "user_input":
                    message = data["command"]["message"]
                    if message == None: 
                        self.sio.emit(
                            "text",
                            {
                                "room": data["room"],
                                "message": COLOR_MESSAGE.format(
                                    color=ERROR_DIALOGUE_COLOR,
                                    message="Please rate the dialogues before moving to the next one.",
                                ),
                                "receiver_id": data["user"]["id"],
                                "html": True,
                            },
                            callback=self.message_callback,
                        )
                        return

                    logging.debug(f"User input received: {message} and saving it")
                    data_to_save = {
                        "dialogue_id": self.current_dialogue_id,
                        "dialogue": self.current_dialogue,
                        "user_choice": message.strip(),
                    }
                    self.log_event("save_user_input", data_to_save, room_id)

                    self.sio.emit(
                        "text",
                        {
                            "room": data["room"],
                            "message": COLOR_MESSAGE.format(
                                color=NEXT_DIALOGUE_COLOR,
                                message="User input saved. Moving to the next dialogue.",
                            ),
                            "receiver_id": data["user"]["id"],
                            "html": True,
                        },
                        callback=self.message_callback,
                    )
                    #load a new board
                    logging.debug(f"Marking the current dialogue {self.current_dialogue_id} as completed")
                    self.dataloader.mark_as_completed(self.current_dialogue_id)
                    logging.debug(f"Loading next dialogue")
                    self.load_dialogues(room_id, user_id)                   
            else:
                # commands received from the user
                # chat-area is disabled, so no need to process any commands
                logging.error(f"Unknown command received: {data}")            


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = EvalDlgQuality.create_argparser()
    args = parser.parse_args()

    # create bot instance
    edt_bot = EvalDlgQuality(args.token, args.user, args.task, args.host, args.port)
    # connect to chat server
    edt_bot.run()
