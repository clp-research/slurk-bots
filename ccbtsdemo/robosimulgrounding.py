import re
import logging
import json
from pathlib import Path
#logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.resolve()
RELATED_FILE_PATH = Path(
    f"{ROOT}"
)

class SimulGrounding:
    def __init__(self, gridwidth, gridheight):
        self.gridwidth = gridwidth
        self.gridheight = gridheight
        self.positions = self.readconfig()

    def readconfig(self):
        with open(f"{RELATED_FILE_PATH}/simulgroundconfig.json") as f:
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
        
    def _get_shape_color(self, code):
        pattern = r"shape\s*=\s*'(.*?)'\s*,\s*color\s*=\s*'(.*?)'"
        match = re.search(pattern, code)
        if match:
            shape, color = match.groups()
            return shape, color
        else:
            return None, None



    def get_positions(self, code):
        target_positions = []
        for c_ in code:
            x, y = self._get_x_y(c_)
            if x is None and y is None:
                continue
            shape, color = self._get_shape_color(c_)
            target_positions.append((shape, color, self.positions["target"][str(x)][str(y)]))
        return target_positions
