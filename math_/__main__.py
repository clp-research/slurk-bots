import ast
import logging
import re

from templates import TaskBot


class MathBot(TaskBot):
    def __init__(self, token, user, task, host, port):
        super().__init__(token, user, task, host, port)

        self.room_to_q = dict()

    def register_callbacks(self):
        @self.sio.event
        def command(data):
            room_id = data["room"]
            user_id = data["user"]["id"]
            cmd = data["command"]

            if cmd.startswith("question"):
                self._set_question(room_id, user_id, cmd)
            elif cmd.startswith("answer"):
                self._give_answer(room_id, user_id, cmd)
            else:
                # inform the user in case of an invalid command
                self.sio.emit(
                    "text",
                    {
                        "message": f"`{cmd}` is not a valid command.",
                        "room": room_id, "receiver_id": user_id
                    },
                    callback=self.message_callback
                )

    def _set_question(self, room_id, user_id, cmd):
        question = re.sub(r"^question\s*", "", cmd)
        solution = self._eval(question)

        if solution is None:
            self.sio.emit(
                "text",
                {
                    "message": "Questions must be mathematical expressions.",
                    "room": room_id, "receiver_id": user_id
                },
                callback=self.message_callback
            )
        else:
            self.room_to_q[room_id] = {
                "question": question, "solution": solution, "sender": user_id
            }
            self.sio.emit(
                "text",
                {
                    "message": f"A new question has been created:\n{question}",
                    "room": room_id
                },
                callback=self.message_callback
            )

    def _give_answer(self, room_id, user_id, cmd):
        answer = re.sub(r"^answer\s*", "", cmd)
        prop_solution = self._eval(answer, answer=True)

        if room_id not in self.room_to_q:
            self.sio.emit(
                "text",
                {
                    "message": "Ups, no question found you could answer!",
                    "room": room_id, "receiver_id": user_id
                },
                callback=self.message_callback
            )
        elif self.room_to_q[room_id]["sender"] == user_id:
            self.sio.emit(
                "text",
                {
                    "message": "Come on! Don't answer your own question.",
                    "room": room_id, "receiver_id": user_id
                },
                callback=self.message_callback
            )
        elif prop_solution is None:
            self.sio.emit(
                "text",
                {
                    "message": "What? Sure that's a number?",
                    "room": room_id, "receiver_id": user_id
                },
                callback=self.message_callback
            )
        else:
            self.sio.emit(
                "text",
                {
                    "message": f"The proposed answer is: {answer}",
                    "room": room_id
                },
                callback=self.message_callback
            )
            if prop_solution == self.room_to_q[room_id]["solution"]:
                self.sio.emit(
                    "text",
                    {
                        "message": "Wow! That's indeed correct.",
                        "room": room_id
                    },
                    callback=self.message_callback
                )
                self.room_to_q.pop(room_id)
            else:
                self.sio.emit(
                    "text",
                    {
                        "message": "Naahh. Try again!",
                        "room": room_id
                    },
                    callback=self.message_callback
                )

    @staticmethod
    def _eval(expr, answer=False):
        try:
            tree = ast.parse(expr, mode='eval')
        except SyntaxError:
            return
        # verify the expression
        for node in ast.walk(tree.body):
            if not isinstance(node, (
                ast.Num, ast.Sub, ast.Add, ast.Mult,
                ast.BinOp, ast.USub, ast.UnaryOp
            )):
                return
            # an answer should not be a complex formula
            if answer and not isinstance(node, (
                ast.Num, ast.USub, ast.UnaryOp
            )):
                return
        return eval(expr)


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = MathBot.create_argparser()
    args = parser.parse_args()

    # create bot instance
    math_bot = MathBot(args.token, args.user, args.task, args.host, args.port)
    # connect to chat server
    math_bot.run()
