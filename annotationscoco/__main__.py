import logging
from threading import Timer
from time import sleep
import requests

from templates import TaskBot
from .preparedata import Dataloader

TIMEOUT_TIMER = 60  # minutes
COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"


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

class AnnotationsCoCo(TaskBot):
    timers_per_room = dict()

    def __init__(self, token, user, task, host, port):
        logging.debug(f"CCBTS Annotations: __init__, task = {task}, user = {user}")
        super().__init__(token, user, task, host, port)
        self.num_images = 0
     

    def on_task_room_creation(self, data):
        logging.debug(f"Task room created, data = {data}")        
        room_id = data["room"]
        task_id = data["task"]        

        self.num_images = 0
        self.dataloader = Dataloader()         

        if task_id is not None and task_id == self.task_id:
            self.disable_chat_area(room_id)
            self.timers_per_room[room_id] = RoomTimer(self.close_room, room_id)

            logging.debug(
                f"Calling modify_Layout for room {room_id} task_id = {task_id}"
            )
            # move the chat | task area divider
            self.modify_layout(room_id)
            sleep(0.5)

            for usr in data["users"]:
                logging.debug(
                    f"Loading input grid during task creation room_id: {room_id} user_id: {usr['id']}"
                )

                self.showwelcomemessage(room_id, usr["id"])
                self.load_target_image(room_id, usr["id"])


    def disable_chat_area(self, room_id):
        """Set room to read only."""
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

        response = requests.get(
            f"{self.uri}/rooms/{room_id}/users",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not get user: {response.status_code}")   

        return response     

    def close_room(self, room_id):
        self.dataloader.save_image_viewing_status()
        self.room_to_read_only(room_id)
        self.timers_per_room.pop(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        # set room to read-only
        response = self.disable_chat_area(room_id)

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


    def load_target_image(self, room_id, user_id):
        """Load the target image."""
        logging.debug(f"Inside load_target_image, room_id = {room_id}, user_id = {user_id}")
        self.num_images += 1

        if self.num_images >= 11:
            #User has annotated 10 images, close the room
            logging.debug("User has annotated 10 images, close the room")

            self.sio.emit(
                "message_command",
                {
                    "command": {"event": "close_after_10_images", "message": ""},
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
                        message="You have done 10 images, please take a break and get back to me later. Room is closing now",
                    ),
                    "receiver_id": user_id,
                    "html": True,
                },
                callback=self.message_callback,
            ) 

            self.close_room(room_id)
            return

        target_image_name, base64_string, legendimage_base64 = self.dataloader.get_target_image()


        if not base64_string:
            logging.error("No target images available for loading")
            self.sio.emit(
                "text",
                {
                    "room": room_id,
                    "message": COLOR_MESSAGE.format(
                        color=STANDARD_COLOR,
                        message="No target images available for loading, recheck later",
                    ),
                    "receiver_id": user_id,
                    "html": True,
                },
                callback=self.message_callback,
            )           
            #Setting empty world state
            base64_string = self.dataloader.get_empty_world_state()

        self.target_image_name = target_image_name
        logging.debug(f"Sending target image to room {room_id}")
        self.sio.emit(
            "message_command",
            {
                "command": {"event": "set_target_image", "message": {"target_board": base64_string, "legend_image": legendimage_base64}},
                "room": room_id,
                "receiver_id": user_id,
            },
        )

    def showwelcomemessage(self, room_id, user_id):
        """Show welcome message."""
        logging.debug(f"Inside showwelcomemessage, room_id = {room_id}, user_id = {user_id}")
        welcome_message = "Welcome to the COCOBOT Annotation Task Room <br><br> You can start by writing down the instructions for the given board<br><br>"
        #Downloaded the image from this site: https://apps.timwhitlock.info/emoji/tables/unicode
        #Emoji: SCROLL, U+1F4DC
        task_message = "Read the instructions on the right ⏩<br>"
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
                if event == "user_input":
                    message = data["command"]["message"]
                    data_to_save = {
                        "target_image_name": self.target_image_name,
                        "message": message
                    }
                    self.log_event("user_instruction", data_to_save, room_id)
                    self.sio.emit(
                        "text",
                        {
                            "room": data["room"],
                            "message": "Saved the instructions",
                            "receiver_id": data["user"]["id"]
                        },
                    )
                    #load a new board
                    logging.debug("Read the instructions, load a new board, clear the text area")
                    self.dataloader.save_image_viewing_status()
                    self.load_target_image(room_id, user_id)

                    #clear the text area
                    logging.debug("clearing the text area")
                    self.sio.emit(
                        "message_command",
                        {
                            "command": {"event": "clear_text_area"},
                            "room": room_id,
                            "receiver_id": data["user"]["id"],
                        }
                    )                    
            else:
                # commands received from the user
                # chat-area is disabled, so no need to process any commands
                logging.error(f"Unknown command received: {data}")




if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = AnnotationsCoCo.create_argparser()
    args = parser.parse_args()

    # create bot instance
    annotations_bot = AnnotationsCoCo(args.token, args.user, args.task, args.host, args.port)
    # connect to chat server
    annotations_bot.run()
