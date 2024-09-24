import pybullet as p
import pybullet_data
import time
import numpy as np
import threading


class RoboarmGripper:
    def __init__(self, ur5_arm, ee_link_id):
        self.ur5_arm = ur5_arm
        gripper_pos = [0.1339999999999999, -0.49199999999872496, 0.5]
        gripper_rot = p.getQuaternionFromEuler([np.pi, 0, np.pi])
        self.ur5_gripper = p.loadURDF("ur5_arm/robotiq_2f_85/robotiq_2f_85.urdf", gripper_pos, gripper_rot)
        self.ur5_gripper_joints = p.getNumJoints(self.ur5_gripper)

        # Connect gripper base to robot tool.
        p.createConstraint(self.ur5_arm, ee_link_id, self.ur5_gripper, 0, jointType=p.JOINT_FIXED,
                        jointAxis=[0, 0, 0], parentFramePosition=[0, 0, 0], childFramePosition=[0, 0, -0.07],
                        childFrameOrientation=p.getQuaternionFromEuler([0, 0, np.pi / 2]))

        # Set friction coefficients for gripper fingers.
        for i in range(p.getNumJoints(self.ur5_gripper)):
            p.changeDynamics(self.ur5_gripper, i, lateralFriction=10.0, spinningFriction=1.0, rollingFriction=1.0, frictionAnchor=True)

        # Open the gripper
        self.motor_joint = 1
        self.open_gripper()

        self.gripper_running = True
        constraints_thread = threading.Thread(target=self.gripper_step)
        constraints_thread.daemon = True
        constraints_thread.start()

    def gripper_step(self):
        while self.gripper_running:
            try:
                currj = [p.getJointState(self.ur5_gripper, i)[0] for i in range(self.ur5_gripper_joints)]
                indj = [6, 3, 8, 5, 10]
                targj = [currj[1], -currj[1], -currj[1], currj[1], currj[1]]
                p.setJointMotorControlArray(self.ur5_gripper, indj, p.POSITION_CONTROL, targj, positionGains=np.ones(5))
            except:
                return
            time.sleep(0.001)

    def close_gripper(self):
        # Close the gripper
        p.setJointMotorControl2(self.ur5_gripper, self.motor_joint, p.VELOCITY_CONTROL, targetVelocity=1, force=10)

    def open_gripper(self):
        # Open the gripper
        p.setJointMotorControl2(self.ur5_gripper, self.motor_joint, p.VELOCITY_CONTROL, targetVelocity=-1, force=10)


class UR5Arm:
    def __init__(self):
        physicsClient = p.connect(p.GUI)  # or p.DIRECT for non-graphical version
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)

        plane_id = p.loadURDF("plane.urdf")

        self.ur5_arm = p.loadURDF("ur5_arm/ur5e/ur5e.urdf", [0, 0, 0], useFixedBase=True)
        joint_ids = [p.getJointInfo(self.ur5_arm, i) for i in range(p.getNumJoints(self.ur5_arm))]
        self.joint_ids = [j[0] for j in joint_ids if j[2] == p.JOINT_REVOLUTE]
        home_joints = (np.pi / 2, -np.pi / 2, np.pi / 2, -np.pi / 2, 3 * np.pi / 2, 0)  # Joint angles: (J0, J1, J2, J3, J4, J5).

        for i in range(len(self.joint_ids)):
            p.resetJointState(self.ur5_arm, self.joint_ids[i], home_joints[i])

        # Add the gripper to the UR5 arm
        ee_link_id = 9  # Link ID of UR5 end effector.
        self.gripper = RoboarmGripper(self.ur5_arm, ee_link_id)

        self.shape_pos = {}
        self.use_pos = 0

    def euler_to_quaternion(self, roll, pitch, yaw):
        cy = np.cos(yaw * 0.5)
        sy = np.sin(yaw * 0.5)
        cp = np.cos(pitch * 0.5)
        sp = np.sin(pitch * 0.5)
        cr = np.cos(roll * 0.5)
        sr = np.sin(roll * 0.5)

        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy

        return [x, y, z, w]

    def load_objects(self):
        washerorn = self.euler_to_quaternion(np.pi / 2, 0, 0)
        rect_washer_id = p.loadURDF("ccbtsshapes/rectangular_washer/washer.urdf", [0.5, -0.2, 0.], washerorn)
        p.changeVisualShape(rect_washer_id, -1, rgbaColor=[1, 0, 0, 1])
        self.shape_pos["washer"] = {"red":[{"id": rect_washer_id, "pos": [0.5, -0.2, 0.]}]}

        rect_washer_id = p.loadURDF("ccbtsshapes/rectangular_washer/washer.urdf", [0.5, -0.5, 0.], washerorn)
        p.changeVisualShape(rect_washer_id, -1, rgbaColor=[0, 1, 0, 1])
        self.shape_pos["washer"]["green"] = [{"id": rect_washer_id, "pos": [0.5, -0.5, 0.]}]

        nutorn = self.euler_to_quaternion(np.pi / 2, 0, 0)
        hex_nut_id = p.loadURDF("ccbtsshapes/hex_nut/nut.urdf", [0.7, -0.2, 0.], nutorn)
        p.changeVisualShape(hex_nut_id, -1, rgbaColor=[0, 0, 1, 1])
        self.shape_pos["nut"] = {"blue": [{"id": hex_nut_id, "pos": [0.7, -0.2, 0.]}]}

        hex_nut_id = p.loadURDF("ccbtsshapes/hex_nut/nut.urdf", [0.7, -0.5, 0.], nutorn)
        p.changeVisualShape(hex_nut_id, -1, rgbaColor=[1, 1, 0, 1])
        self.shape_pos["nut"]["yellow"] = [{"id": hex_nut_id, "pos": [0.7, -0.5, 0.]}]


        hex_screw_id = p.loadURDF("ccbtsshapes/hexagonal_screw/screw.urdf", [0.3, -0.2, 0.])
        p.changeVisualShape(hex_screw_id, -1, rgbaColor=[1, 0, 0, 1])
        self.shape_pos["screw"] = {"red": [{"id": hex_screw_id, "pos": [0.3, -0.2, 0.]}]}

        hex_screw_id = p.loadURDF("ccbtsshapes/hexagonal_screw/screw.urdf", [0.3, -0.5, 0.])
        p.changeVisualShape(hex_screw_id, -1, rgbaColor=[0, 0, 1, 1])
        self.shape_pos["screw"]["blue"] = [{"id": hex_nut_id, "pos": [0.3, -0.5, 0.]}]



    def servoj(self, joints):
        """Move to target joint positions with position control."""
        p.setJointMotorControlArray(
        bodyIndex=self.ur5_arm,
        jointIndices=self.joint_ids,
        controlMode=p.POSITION_CONTROL,
        targetPositions=joints,
        positionGains=[0.01]*6)

    def movep(self, position, tip_link_id=10, home_ee_euler=(np.pi, 0, np.pi)):
        """Move to target end effector position."""
        joints = p.calculateInverseKinematics(
            bodyUniqueId=self.ur5_arm,
            endEffectorLinkIndex=tip_link_id,
            targetPosition=position,
            targetOrientation=p.getQuaternionFromEuler(home_ee_euler),
            maxNumIterations=100)
        self.servoj(joints)

    def stepsimulation(self, time_range=240):
        for _ in range(time_range):
            p.stepSimulation()
            time.sleep(1./240.)



    def _pick_object(self, position):
        text_position = [position[0], position[1], position[2] + 0.1]
        p.addUserDebugText(f'S', textPosition=text_position, textColorRGB=[1,0,1], textSize=1) # display goal
        
        # Hover over the object
        target_position = [position[0], position[1], position[2] + 0.05]
        print(f"Hovering over the object at {target_position}")
        self.movep(target_position)
        self.stepsimulation()

        # Go down to the object
        pick_position = [position[0], position[1], position[2] + 0.02]
        print(f"Going down to the object at {pick_position}")
        self.movep(pick_position)
        self.stepsimulation()
        
        # Close the gripper and lift the object
        self.gripper.close_gripper()
        self.stepsimulation()  
        
        # Go up
        target_position = [position[0], position[1], 0.2]
        print(f"Going up to {target_position}")
        self.movep([0.5, 0.1, 0.2])
        self.stepsimulation()

    def _place_object(self, position):
        #Move to a new position
        text_position = [position[0], position[1], position[2] + 0.1]
        p.addUserDebugText(f'T', textPosition=text_position, textColorRGB=[1,0,1], textSize=1) # display goal

        # Hover over the target position
        target_position = [position[0], position[1], 0.2]
        print(f"Hovering over the target position at {target_position}")
        self.movep(target_position)
        self.stepsimulation()

        # Lower the gripper
        lower_pos = [position[0], position[1], 0.03]
        print(f"Lowering the gripper to {lower_pos}")
        self.movep(lower_pos)
        self.stepsimulation(500)

        # Open the gripper
        self.gripper.open_gripper()
        self.stepsimulation()

        # Back to the original position
        target_position = [position[0], position[1], 0.5]
        self.movep(target_position)
        self.stepsimulation()


    def pickandplace(self, target_positions):
        if not target_positions:
            return

        for target in target_positions:
            shape, color, pos = target
            print(f"Moving {shape} {color} to {pos}")
            self._pick_object(self.shape_pos[shape][color][0]["pos"])
            self._place_object(pos)



