import random

class Controller:
    def __init__(self):
        self.elements = ["\u25CA", "\u25CB", "\u2021"]
        self.images = [
            "https://upload.wikimedia.org/wikipedia/commons/d/d8/Sailboat_Flat_Icon_Vector.svg"
        ]
        self.random_boards()

    def random_boards(self):
        self.source = [
            [" ".join(random.choices(self.elements, k=4)) for i in range(3)]
            for j in range(4)
        ]
        self.target = [
            [" ".join(random.choices(self.elements, k=4)) for i in range(4)]
            for j in range(4)
        ]

    def get_boards(self):
        return self.source, self.target

    def enter_command(self, command):
        self.random_boards()

    def get_image(self):
        return self.images[0]