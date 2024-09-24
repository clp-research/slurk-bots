import logging
from threading import Timer
from time import sleep

import requests

from templates import TaskBot

from .getllmresponse import PromptLLM
from .preparedata import Dataloader
from .execresponse import execute_response
from .base64encode import encode_image_to_base64
from .dmanager import DialogueManager



TIMEOUT_TIMER = 60  # minutes

COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
RESPONSE_COLOR = "Green"


class RoomTimer:
    def __init__(self, function, room_id):
        self.function = function
        self.room_id = room_id
        self.start_timer()

    def start_timer(self):
        self.timer = Timer(TIMEOUT_TIMER * 60, self.function, args=[self.room_id])
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        logging.debug("reset timer")

    def cancel(self):
        self.timer.cancel()


class CCBTSDemoBot(TaskBot):
    timers_per_room = dict()

    def __init__(self, token, user, task, host, port):
        logging.debug(f"CCBTS: __init__, task = {task}, user = {user}")
        super().__init__(token, user, task, host, port)
        self.n_turns = 0
        self.instructions = {}
        self.model_response = {}
        self.rows = 8
        self.cols = 8
        self.dataloader = Dataloader()
        #logging.debug(f"CCBTS: Calling Dialogue Manager")
        #self.dmanager = DialogueManager({"width":self.cols, "height":self.rows})
        #sleep(1)
        logging.debug(f"CCBTS: __init__ completed, task = {task}, user = {user}")

    def load_rasa_model(self):
        logging.debug(f"CCBTS: Calling Dialogue Manager")
        self.dmanager = DialogueManager({"width":self.cols, "height":self.rows})
        logging.debug(f"CCBTS: loaded the model")

    def on_task_room_creation(self, data):
        logging.debug(f"Task room created, data = {data}")
        room_id = data["room"]
        task_id = data["task"]

        if task_id is not None and task_id == self.task_id:
            self.timers_per_room[room_id] = RoomTimer(self.close_room, room_id)

            logging.debug(
                f"Calling modify_Layout for room {room_id} task_id = {task_id}"
            )
            # move the chat | task area divider
            self.modify_layout(room_id)
            sleep(0.5)

            self._cleanup(room_id, None)

            # set the empty grid as the world state
            for usr in data["users"]:
                logging.debug(
                    f"Setting empty grid during task creation room_id: {room_id} user_id: {usr['id']}"
                )

                self.dmanager = DialogueManager()#{"width":self.cols, "height":self.rows})
                #sleep(1)
                self.simulationtype = self.dmanager.getsimulationtype()

                self.rearrange_layout(room_id, usr["id"], self.simulationtype)
                self.load_target_image(room_id, usr["id"])
                self.setworldstate(room_id, usr["id"])
                self.showwelcomemessage(room_id, usr["id"])
        else:
            logging.debug(f"Task ID {task_id} does not match {self.task_id}")


    def close_room(self, room_id):
        logging.debug(f"Closing room {room_id}") 
        self._cleanup(room_id, None)
        self.room_to_read_only(room_id)
        self.timers_per_room.pop(room_id)

    def room_to_read_only(self, room_id):
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
                "value": f"height: 90%; width:70%; top: 40px",
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
        welcome_message = "Welcome to the Task Room <br><br> You can start by typing your instructions in the chat area<br><br>"
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

    def hideworkingboard(self, room_id, user_id):
        """Hide the working board."""
        self.sio.emit(
            "message_command",
            {
                "command": {"event": "hide_working_board"},
                "room": room_id,
                "receiver_id": user_id,
            },
        )

    def rearrange_layout(self, room_id, user_id, simulation_type):
        logging.debug(f"rearrange_layout: simulation_type = {simulation_type}")
        # If simulation_type is not virtual (2.5 world), hide the working board
        if simulation_type != "virtual":
            logging.debug(f"simulation_type != virtual, calling hideworkingboard")
            self.hideworkingboard(room_id, user_id)

    def load_target_image(self, room_id, user_id):
        """Load the target image."""
        logging.debug(f"Inside load_target_image, room_id = {room_id}, user_id = {user_id}")
        base64_string = self.dataloader.get_target_image()
        self.sio.emit(
            "message_command",
            {
                "command": {"event": "set_target_image", "message": base64_string},
                "room": room_id,
                "receiver_id": user_id,
            },
        )

    def setworldstate(self, room_id, user_id):
        logging.debug(f"Inside setworldstate, room_id = {room_id}, user_id = {user_id}")
        #save_filename = resetboardstate(self.rows, self.cols)
        #base64_string = encode_image_to_base64(save_filename)#get_empty_world_state()

        if self.simulationtype != "virtual":
            event_name = "hide_working_board"
            base64_string = ""
        else:
            event_name = "update_world_state"
            base64_string = self.dataloader.get_empty_world_state()

        self.sio.emit(
            "message_command",
            {
                "command": {"event": event_name, "message": base64_string},
                "room": room_id,
                "receiver_id": user_id,
            },
        )
    
    def _cleanup(self, room_id, user_id):
        logging.debug(f"Doing _cleanup for the room {room_id}, user {user_id}")
        self.n_turns = 0
        self.instructions = {}
        self.model_response = {}

        if user_id is not None:
            #TODO: Check where should this be placed
            timer = self.timers_per_room.get(room_id)
            if timer is not None:
                timer.reset()


            self.setworldstate(room_id, user_id)
            self.dmanager.reset()


    def handlereset(self, room_id, user_id, command="reset"):
        """Handle reset command."""
        logging.debug(f"Received {command} for the room {room_id}, user {user_id}")

        self._cleanup(room_id, user_id)

        if command in ["clear", "reset"]:
            message = "Resets the world state"
        elif command == "restart":
            message = "Resets the target board"
            self.load_target_image(room_id, user_id)

        self.sio.emit(
            "text",
            {
                "room": room_id,
                # "message": message
                "message": COLOR_MESSAGE.format(
                    color=STANDARD_COLOR, message=message
                ),
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

            logging.debug(f"I got a message, let's process it!: {data}")

            options = {}
            if data["private"]:
                logging.debug("It was actually a private message o.O")
                options["receiver_id"] = data["user"]["id"]

            # This is the user instruction
            message = data["message"]

            if not self.dmanager.israsaready():
                self.sio.emit(
                                "text",
                                {
                                    "room": data["room"],
                                    "message": COLOR_MESSAGE.format(
                                        color=STANDARD_COLOR, message="Failure in connecting to RASA Server, Try after a minute"
                                    ),
                                    "html": True,
                                    **options,
                                },
                                callback=self.message_callback,
                            )
                return

            response = self.dmanager.run(message)
            logging.debug(f"Response: {response}")

            #Show the response in the chat area
            if response:
                #if not "png" in response["output"]:
                confidence = str(response["dialogue_act"]["confidence"])
                intent_info = "Rasa Intent Details: "+ "<br>" + "Name: " +response["dialogue_act"]["name"].capitalize() + "<br>" + " Confidence: " +confidence
                intent_info = COLOR_MESSAGE.format(color=STANDARD_COLOR, message=intent_info)

                if "entities" in response:
                    if response["entities"]:
                        entity_info = "Entities:"+ "<br>"
                        for entity_name, entity_value in response["entities"].items():
                            entity_info += entity_name.capitalize() + ": " + entity_value + "<br>"
                        intent_info += "<br>" + COLOR_MESSAGE.format(color=STANDARD_COLOR, message=entity_info)
                '''
                if response['llmresponse'] and response['llmresponse']['Intent'] and response['llmresponse']['Confidence']:
                    confidence = str(round(response['llmresponse']['Confidence'], 2))
                    llm_intent_info = "LLM Intent Details: "+ "<br>" + "Name: " +response['llmresponse']['Intent'].capitalize() + "<br>" + " Confidence: " +confidence

                    slots = response['llmresponse']['Slots']
                    if slots:
                        llm_intent_info += "<br>" + "Slots: " + "<br>"
                        for slot_name, slot_value in slots.items():
                            logging.debug(f"Slot Name: {slot_name}, Slot Value: {slot_value}")
                            llm_intent_info += slot_name.capitalize()+ ": "
                            if isinstance(slot_value, dict):
                                for key, value in slot_value.items():
                                    llm_intent_info += str(value) + "<br>"
                            else:
                                llm_intent_info += str(slot_value) + "<br>"
                    llm_intent_info = COLOR_MESSAGE.format(color="Blue", message=llm_intent_info)
                '''
                if not "png" in response["output"]:
                    message = response["output"]
                else:
                    if response["dialogue_act"]["name"].lower() == "translate":
                        message = f"Generated Code: <br> {response['code']}"
                    else:    
                        message = f"Code Undo: <br> {response['code']}"

                output = COLOR_MESSAGE.format(color=RESPONSE_COLOR, message=message)


                self.sio.emit(
                                "text",
                                {
                                    "room": data["room"],
                                    "message": intent_info,
                                    #"message": COLOR_MESSAGE.format(
                                    #    color=STANDARD_COLOR, message=output
                                    #),
                                    "html": True,
                                    **options,
                                },
                                callback=self.message_callback,
                            )
                '''
                self.sio.emit(
                                "text",
                                {
                                    "room": data["room"],
                                    "message": llm_intent_info,
                                    #"message": COLOR_MESSAGE.format(
                                    #    color=STANDARD_COLOR, message=output
                                    #),
                                    "html": True,
                                    **options,
                                },
                                callback=self.message_callback,
                            )
                '''
                self.sio.emit(
                                "text",
                                {
                                    "room": data["room"],
                                    "message": output,
                                    #"message": COLOR_MESSAGE.format(
                                    #    color=STANDARD_COLOR, message=output
                                    #),
                                    "html": True,
                                    **options,
                                },
                                callback=self.message_callback,
                            )
                #else:

                if "png" in response["output"]:
                    logging.debug(f"Code: {response['code']}\nSimulation Type = {self.simulationtype}")


                    self.sio.emit(
                                    "text",
                                    {
                                        "room": data["room"],
                                        "message": COLOR_MESSAGE.format(
                                            color=STANDARD_COLOR, message="Updated the working board"
                                        ),
                                        "html": True,
                                        **options,
                                    },
                                    callback=self.message_callback,
                                )  


                    if self.simulationtype == "virtual":
                        base64_string = encode_image_to_base64(response["output"])
                        self.sio.emit(
                            "message_command",
                            {
                                "command": {
                                    "event": "update_world_state",
                                    "message": base64_string,
                                },
                                "room": room_id,
                                "receiver_id": data["user"]["id"],
                            },
                        )
                    elif self.simulationtype == "pybullet":
                        self.dmanager.showpbsimulation(response["code"])

                    elif self.simulationtype == "realarm":
                        self.dmanager.showrealarm(response["code"])
                      

                #if response['code']:
                #    self.dmanager.pickandplace(response['code'])

        @self.sio.event
        def command(data):
            """Parse user commands."""

            logging.debug(f"Received a user command: {data}")

            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process commands from itself
            if user_id == self.user:
                logging.debug(f"user_id == self.user, returning")
                return

            # commands from the user
            if data["command"] in ["clear", "reset"]:
                # clear the board, resets state and other variables
                self.handlereset(room_id, user_id, "reset")
            elif data["command"] == "restart":
                # re-fetch the target board
                self.handlereset(room_id, user_id, "restart")
            else:
                logging.debug(f"Unknown command: {data['command']}")
                self.sio.emit(
                    "text",
                    {
                        "room": room_id,
                        "message": COLOR_MESSAGE.format(
                            color=STANDARD_COLOR, message="Unknown command"
                        ),
                        "receiver_id": user_id,
                        "html": True,
                    },
                    callback=self.message_callback,
                )


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = CCBTSDemoBot.create_argparser()
    args = parser.parse_args()

    # create bot instance
    ccbts_demo_bot = CCBTSDemoBot(args.token, args.user, args.task, args.host, args.port)
    #ccbts_demo_bot.load_rasa_model()
    # connect to chat server
    ccbts_demo_bot.run()
