import logging
import requests
import re
import json




class PBInterface:
    def __init__(self, base_url):
        self.base_url = base_url

    # Function to initialize the simulation
    def initialize_simulation(self):
        response = requests.post(f"{self.base_url}/initialize", headers={"Content-Type": "application/json"}, json={})
        if response.status_code == 200:
            data = response.json()
            logging.debug(f"Pybullet Initialization successful: {data}")

            #self.robotId = data["robotId"]
            #self.jointIDs = data["joint_ids"]
            #self.shapes = data["shapes"]

        else:
            logging.debug(f"Error initializing simulation: {response.text}")

    # Function to initialize the simulation
    def loadshapes(self):
        response = requests.post(f"{self.base_url}/loadshapes", headers={"Content-Type": "application/json"}, json={})
        if response.status_code == 200:
            data = response.json()
            print("loadshapes successful:", data)
        else:
            print("Error in loadshapes:", response.text)            

    def _extract_values(self, code):
        match = re.search(r"shape\s*=\s*'(.*?)'\s*,\s*color\s*=\s*'(.*?)'\s*,\s*x\s*=\s*(\d+)\s*,\s*y\s*=\s*(\d+)", code)
        if match is None:
            match = re.search(r"put\(board,\s*shape=('\w+?'),\s*color=('\w+?'),\s*x=(\d+),\s*y=(\d+)\)", code)
        if match:
            return match.groups()

        else:
            return None, None, None, None

        
    # Function to perform the pick and place operation
    def perform_pick_and_place(self, code_list):
        logging.debug(f"Inside perform_pick_and_place: code_list = {code_list}")
        #payload = {"robotId": self.robotId, "joint_ids": self.jointIDs, "shapes": self.shapes}
        for code in code_list:
            shape, color, x, y = self._extract_values(code)
            payload = {"shape": shape, 'color': color, 'x': x, 'y': y}
            response = requests.post(f"{self.base_url}/pick_and_place", headers={"Content-Type": "application/json"}, json=payload)
            if response.status_code == 200:
                logging.debug("Pick and place operation completed")
                logging.debug(response.json())
            else:
                logging.debug(f"Error during pick and place operation: {response.text}")