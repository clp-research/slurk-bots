import time
import re
import json
from pathlib import Path

from .ur_python_tryout import RobotController
import logging

ROOT = Path(__file__).parent.resolve()
RELATED_FILE_PATH = Path(
    f"{ROOT}"
)
class ActionGrounding:
    def __init__(self):
        self.locations = self.readfile()
        #self.rc = RobotController()

    def readfile(self):
        with open(f"{RELATED_FILE_PATH}/physicallocations.json", "r") as f:
            return json.load(f)

    def _get_x_y(self, code):
        match = re.search(r'x=(\d+),\s*y=(\d+)', code)
        if not match:
            # If not found, try to match the position format
            match = re.search(r"put\(board,\s*'\w+?',\s*'\w+?',\s*(\d+),\s*(\d+)\)", code)
        if match:
            x, y = match.groups()
            return x, y
        else:
            return None, None

    def run(self, code):
        for index, c_ in enumerate(code):
            x, y = self._get_x_y(c_)
            print(f"Code = {c_}, x = {x}, y = {y}")
            logging.debug(f"Code = {c_}, x = {x}, y = {y}")
            source_x = self.locations["source"]["x"][str(x)]
            source_y = self.locations["source"]["y"][str(y)]
            target_x = self.locations["target"]["x"][str(x)]
            target_y = self.locations["target"]["y"][str(y)]
            print(f"source_x = {source_x}, source_y = {source_y}, target_x = {target_x}, target_y = {target_y}")
            self.rc.goto_source(source_x, source_y)
            self.rc.goto_target(target_x, target_y)
            time.sleep(1)
        print("Successfully executed the code on UR arm")



    def run_sampletest(self, code):
        source_x = [0.2331, 0.3331, 0.4331]
        target_x = [0.4311, 0.4371, 0.4391]
        source_y = [-0.22, -0.22, -0.22]
        target_y = [-0.02, -0.07, -0.12]
        for index, c_ in enumerate(code):
            x, y = self._get_x_y(c_)
            print(f"Code = {c_}, x = {x}, y = {y}")
            #source_x = self.locations["source"]["x"][str(x)]
            #source_y = self.locations["source"]["y"][str(y)]
            #target_x = self.locations["target"]["x"][str(x)]
            #target_y = self.locations["target"]["y"][str(y)]
            print(f"source_x = {source_x[index]}, source_y = {source_y[index]}, target_x = {target_x[index]}, target_y = {target_y[index]}")
            self.rc.goto_source(source_x[index], source_y[index])
            self.rc.goto_target(target_x[index], target_y[index])
            time.sleep(1)
        print("Successfully executed the code on UR arm")


    def perform_pick_and_place(self, code):
        self.run(code)


if __name__ == "__main__":
    ag = ActionGrounding()
    code =  ["code1", "code2"]
    ag.run_sampletest(code)
    print("Done")