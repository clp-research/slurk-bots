"""Slurk (Task)Bot template classes."""

import argparse
import logging
import os

import requests  # NOQA
import socketio


class Bot:
    sio = socketio.Client(logger=True)

    def __init__(self, token, user, host, port):
        """Serves as a template for bots.

        :param token: A universally unique identifier (UUID);
            e.g. `0c45b30f-d049-43d1-b80d-e3c3a3ca22a0`
        :type token: str
        :param user: ID of a `User` object created from the token
        :type user: int
        :param host: Full URL including protocol and hostname
        :type host: str
        :param port: Port used by the slurk chat server;
            If you use a docker container that publishes an internal
            port to another port on the docker host, specify the latter
        :type port: int
        """
        self.token = token
        self.user = user

        self.uri = host
        if port is not None:
            self.uri += f":{port}"
        self.uri += "/slurk/api"
        logging.info(f"Running {self.__class__.__name__} on {self.uri} ...")

        self.register_callbacks()

    def register_callbacks(self):
        """Register all necessary event handlers."""
        pass

    def run(self):
        """Establish a connections to the slurk chat server."""
        self.sio.connect(
            self.uri,
            headers={
                "Authorization": f"Bearer {self.token}",
                "user": str(self.user)
            },
            namespaces="/",
        )
        self.sio.wait()

    @staticmethod
    def message_callback(success, error_msg="Unknown Error"):
        """Verify whether a call was successful.

        Will be invoked after the server has processed the event,
        any values returned by the event handler will be passed
        as arguments.

        :param success: `True` if the message was successfully sent,
            else `False`
        :type success: bool
        :param error_msg: Reason for an unsuccessful call
        :type status: str, optional
        """
        if not success:
            logging.error(f"Could not send message: {error_msg}")
            raise ValueError(error_msg)
        logging.debug("Message was sent successfully.")

    @staticmethod
    def request_feedback(response, action):
        """Verify whether a request was successful.

        :param response: Response to request
        :type response: requests.models.Response
        :param action: Action meant to be performed
        :type action: str
        """
        if not response.ok:
            logging.error(f"`{action}` unsuccessful: {response.status_code}")
            response.raise_for_status()
        logging.debug(f"`{action}` successful.")

    @classmethod
    def create_argparser(cls):
        """Creates command-line interface to the template class.

        :return: Created commandline argument parser
        :rtype: argparse.ArgumentParser
        """
        parser = argparse.ArgumentParser(
            description=f"Run {cls.__name__}."
        )

        # collect environment variables as defaults
        if "SLURK_TOKEN" in os.environ:
            token = {"default": os.environ["SLURK_TOKEN"]}
        else:
            token = {"required": True}
        if "SLURK_USER" in os.environ:
            user = {"default": os.environ["SLURK_USER"]}
        else:
            user = {"required": True}

        # register commandline arguments
        parser.add_argument(
            "-t", "--token", **token,
            help="slurk token for the bot"
        )
        parser.add_argument(
            "-u", "--user", type=int, **user,
            help="slurk user ID for the bot"
        )
        parser.add_argument(
            "-c", "--host",
            default=os.environ.get("SLURK_HOST", "http://localhost"),
            help="full URL of chat server (protocol and hostname) "
        )
        parser.add_argument(
            "-p", "--port", type=int,
            default=os.environ.get("SLURK_PORT"),
            help="port of chat server"
        )
        return parser


class TaskBot(Bot):
    def __init__(self, token, user, task, host, port):
        """Serves as a template for task bots.

        :param task: Task ID
        :type task: str
        """
        super().__init__(token, user, host, port)
        self.task_id = task
        self.sio.on('new_task_room', self.join_task_room())

    def join_task_room(self):
        """Let the bot join an assigned task room."""
        def join(data):
            if self.task_id is None or data["task"] != self.task_id:
                return

            response = requests.post(
                f"{self.uri}/users/{self.user}/rooms/{data['room']}",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            self.request_feedback(
                response, f"let {self.__class__.__name__}  join room"
            )
        return join

    @classmethod
    def create_argparser(cls):
        # inherit from parent's argparser
        parser = argparse.ArgumentParser(
            description=f"Run {cls.__name__}.",
            parents=[super().create_argparser()],
            add_help=False
        )
        task_bot_name = cls.__name__.upper().replace("BOT", "")

        parser.add_argument(
            "--task", type=int,
            default=os.environ.get(f"{task_bot_name}_TASK_ID"),
            help="slurk task ID the bot should moderate"
        )
        return parser
