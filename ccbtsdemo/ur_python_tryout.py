#### Usage:
#### Check own IP address is still correct (netstat -i)
#### Turn robot on, check own IP address and port in robot installation tab
#### Put robot into remote control mode (button top right)
#### Then simply run this program in terminal :) (>$ python3 <filename.py>)

## Warning: sending commands to quickly replaces old commands before they get executed or interrupts them!
import socket
import time

from pathlib import Path

ROOT = Path(__file__).parent.resolve()
RELATED_FILE_PATH = Path(
    f"{ROOT}/data"
)

HOST = "192.168.0.4"    # Robot IP
PORT = 30002            # Robot Port
MASTER = "192.168.0.3"  # own IP
SCRIPT_FOLDER = f"{RELATED_FILE_PATH}/ur_scripts/"

class RobotController:
    def __init__(self):
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.bind((MASTER, PORT))
        serversocket.listen(5)

        self.sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.sender.connect((HOST, PORT))
        self.first_move = True

    def __del__(self):
        self.sender.close()

    def execute_command(self, string):
        self.sender.send((string + "\n").encode("utf8"))

    def execute_script(self, scriptname):
        print(f"Executing {scriptname}...")
        scriptfile = open(SCRIPT_FOLDER + scriptname, "rb")
        l = scriptfile.read(1024)
        while (l):
            self.sender.send(l)
            l = scriptfile.read(1024)
        print("Done.")
        time.sleep(10)

    def grip(self):
        script = "grip.script"
        self.execute_script(script)
        # necessary as it will otherwise be replaced by the next instruction
        time.sleep(1)
        # TODO: check whether grip was established, then move on

    def release(self):
        script = "release.script"
        self.execute_script(script)
        # necessary as it will otherwise be replaced by the next instruction
        time.sleep(2)
        # TODO: check whether vacuum was released, then move on

    def move_to_xyz(self, x, y, z, acceleration = 1.0, velocity = 0.3):
        self.execute_command(f"movej(p[{x}, {y}, {z}, 0, 3.15, 0], a={acceleration}, v={velocity})")
        # necessary to not interrupt the movement with the next instruction, 
        # duration depends on how long the movement needs to execute
        time.sleep(3)
        # TODO: check whether movement was finished, then move on		

    def get_data(self):
        # TODO: rewrite this to something useful
        self.execute_command("set_digital_out(2,True)" + "\n")
        data = self.sender.recv(1024)
        self.execute_command("set_digital_out(2,False)" + "\n")
        # FIXME: decoding currently does not work
        print("Received", data.decode())

    def get_position(self):
        # TODO: get this working
        self.execute_command("get_actual_tcp_position()")
        data = self.sender.recv(1024)
        print("Position", repr(data))
		
    def goto_source(self, source_x, source_y):
        self.move_to_xyz(source_x, source_y, 0.06, 0.5, 0.2)
        if self.first_move:
            time.sleep(10)
            self.first_move = False
        else:
            time.sleep(2)
        self.grip()

    def goto_target(self, target_x, target_y):
        self.move_to_xyz(target_x, target_y, 0.04, 0.5, 0.2)
        time.sleep(2)
        self.release()

