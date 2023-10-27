import logging
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Tuple

from dynamixel_sdk import (
    PortHandler,
    PacketHandler,
    GroupBulkWrite,
    GroupBulkRead,
    COMM_SUCCESS,
    DXL_LOBYTE,
    DXL_LOWORD,
    DXL_HIBYTE,
    DXL_HIWORD,
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
ROBOT_TOKEN: str = "🤖"
SERVO_TOKEN: str = "🦾"
CAMERA_TOKEN: str = "📷"
POSE_TOKEN: str = "🤸"

@dataclass
class Servo:
    id: int # dynamixel id for servo
    name: str # name of servo for llm use
    range: Tuple[int, int] # (min, max) position values for servos (0, 4095)
    desc: str # description of servo for llm use

SERVOS: List[Servo] = [
    Servo(1, "roll", (1761, 2499), "rolls the neck left and right rotating the view, roll"),
    Servo(2, "tilt", (979, 2223), "tilts the head up and down vertically, pitch"),
    Servo(3, "pan", (988, 3007), "pans the head side to side horizontally, yaw")
]

@dataclass
class Pose:
    name: str # name of pose for llm use
    angles: List[int] # list of int angles in degrees (0, 360)
    desc: str # description of position for llm use

POSES: Dict[str, Pose] = {
    "home" : Pose("home", [180, 211, 180], "home position or look up"),
    "forward" : Pose("forward", [180, 140, 180], "look ahead, facing forward"),
    "tilt left" : Pose("tilt left", [215, 130, 151], "looking forward, head tilted right"),
    "tilt right" : Pose("tilt right", [145, 130, 209], "looking forward, head tilted left"),
    "down": Pose("down", [180, 94, 180], "looking down, facing forward")
}

ROBOT_DESCRIPTION: str = f"""
You are an llm control unit for a robot arm called {ROBOT_TOKEN}.
{ROBOT_TOKEN} has with servos {SERVO_TOKEN} forming a kinematic chain.
The Servo dataclass holds information for each {SERVO_TOKEN}:

@dataclass
class Servo:
    id: int # dynamixel id for servo
    name: str # name of servo for llm use
    range: Tuple[int, int] # (min, max) position values for servos (0, 4095)
    desc: str # description of servo for llm use

{ROBOT_TOKEN} can be put into different poses {POSE_TOKEN}.
Each pose contains angles in degrees for each {SERVO_TOKEN}.
The Pose dataclass holds information for each pose:

@dataclass
class Pose:
    name: str # name of pose for llm use
    angles: List[int] # list of int angles in degrees (0, 360)
    desc: str # description of position for llm use

{ROBOT_TOKEN} can take images with a camera {CAMERA_TOKEN}.
The Camera dataclass holds information for {CAMERA_TOKEN}:

@dataclass
class Camera:
    id: int # id for camera
    name: str # name of camera for llm use
    width: int # width of image in pixels
    height: int # height of image in pixels
    desc: str # description of camera for llm use

{ROBOT_TOKEN} has the following components
{SERVO_TOKEN}: List[Servo] = [
    Servo(1, "roll", (1761, 2499), "rolls the neck left and right rotating the view, roll"),
    Servo(2, "tilt", (979, 2223), "tilts the head up and down vertically, pitch"),
    Servo(3, "pan", (988, 3007), "pans the head side to side horizontally, yaw")
]
POSES: List[Pose] = [
    Pose("home", [180, 211, 180], "home position or look up"),
    Pose("forward", [180, 140, 180], "look ahead, facing forward"),
    Pose("tilt left", [215, 130, 151], "looking forward, head tilted right"),
    Pose("tilt right", [145, 130, 209], "looking forward, head tilted left"),
    Pose("down", [180, 94, 180], "looking down, facing forward")
]
"""

ACTION_DESCRIPTION: str = f"""
The user will describe in natural language a command.
Format the command so that {ROBOT_TOKEN} can understand it.
{ROBOT_TOKEN} will then execute the command.
{ROBOT_TOKEN} can accept the following commands:
   - {SERVO_TOKEN}: move to a specific pose based on description
   - {CAMERA_TOKEN}: take a picture with the camera
"""

MOVE_DESCRIPTION: str = f"""
{ROBOT_TOKEN} is going to {SERVO_TOKEN}.
Based on the user description, choose a pose from the following list [{", ".join(POSES.keys())}].
You must return an exact match to name of one of the poses.

"go to the home position" -> "home"
"face the forward direction" -> "forward"
"look down" -> "down"
The user will now describe a pose, return the name of one of the valid poses.
"""

# Convert servo units into degrees for readability
# Max for units is 4095, which is 360 degrees
DEGREE_TO_UNIT: float = 4095 / 360.0

def degrees_to_units(degree: int) -> int:
    return int(degree * DEGREE_TO_UNIT)

def units_to_degrees(position: int) -> int:
    return int(position / DEGREE_TO_UNIT)

class Robot:

    def __init__(
        self,
        servos: List[Servo] = SERVOS,
        poses: Dict[str, Pose] = POSES,
        desc: str = ROBOT_DESCRIPTION,
        move_desc: str = MOVE_DESCRIPTION,
        protocol_version: float = 2.0,
        baudrate: int = 57600,
        device_name: str = "/dev/ttyUSB0",
        addr_torque_enable: int = 64,
        addr_goal_position: int = 116,
        addr_present_position: int = 132,
        torque_enable: int = 1,
        torque_disable: int = 0,
    ):
        self.servos = servos  # List of Servo objects to control
        for servo in self.servos:
            log.debug("---- Initialize servo ----")
            log.debug(f"servo: {servo.name}")
            log.debug(f"id: {servo.id}")
            log.debug(f"range: {servo.range}")
            log.debug(f"description: {servo.desc}")
        self.num_servos: int = len(self.servos)  # Number of servos to control
        self.poses = poses # Dict of Pose objects to control
        self.desc = desc # Description of robot for llm use
        self.move_desc = move_desc # Description of move for llm use

        # Dynamixel communication parameters
        self.protocol_version = protocol_version  # DYNAMIXEL Protocol version (1.0 or 2.0)
        self.baudrate = baudrate  # Baudrate for DYNAMIXEL communication
        self.device_name = device_name  # Name of the device (port) where DYNAMIXELs are connected
        self.addr_torque_enable = addr_torque_enable  # Address for Torque Enable control table in DYNAMIXEL
        self.addr_goal_position = addr_goal_position  # Address for Goal Position control table in DYNAMIXEL
        self.addr_present_position = addr_present_position  # Address for Present Position control table in DYNAMIXEL
        self.torque_enable = torque_enable  # Value to enable the torque
        self.torque_disable = torque_disable  # Value to disable the torque

        # Initialize DYNAMIXEL communication
        self.port_handler = PortHandler(self.device_name)
        self.packet_handler = PacketHandler(self.protocol_version)
        if not self.port_handler.openPort():
            log.error("Failed to open the port")
            exit()
        if not self.port_handler.setBaudRate(self.baudrate):
            log.error("Failed to change the baudrate")
            exit()
        self.group_bulk_write = GroupBulkWrite(self.port_handler, self.packet_handler)
        self.group_bulk_read = GroupBulkRead(self.port_handler, self.packet_handler)

    def move_with_prompt(self,
        position_str: int = "home",
        llm_func: callable = None,
    ) -> str:
        desired_pose = llm_func(
                max_tokens=8,
                messages=[
                    {"role": "system", "content": self.desc + self.move_desc},
                    {"role": "user", "content": position_str},
                ]
        )
        log.debug(f"Desired pose: {desired_pose}")
        if desired_pose in self.poses:
            log.debug(f"Moving to pose: {desired_pose}")
            return self.move(self.poses[desired_pose].angles)
        else:
            return "Invalid pose."

    def move(
        self,
        goal_positions: List[int],
        epsilon: int = 10, # degrees
        timeout: timedelta = timedelta(seconds=1.0), #timeout
    ) -> str:
        msg: str = ""
        start_time = time.time()
        try:
            while True:
                elapsed_time = time.time() - start_time
                msg += f"{ROBOT_TOKEN} commanded to position {goal_positions}"
                self._write_position(goal_positions)
                true_positions = self._read_pos()
                msg += f"{ROBOT_TOKEN} at position {true_positions}"
                if epsilon > sum(abs(true_positions[i] - goal_positions[i]) for i in range(len(goal_positions))):
                    msg += f"MOVE succeeded in {elapsed_time} seconds."
                    break
                if elapsed_time > timeout.total_seconds():
                    msg += f"MOVE timed out after {elapsed_time} seconds."
                    break 
        except Exception as e:
            msg += f"MOVE failed with exception {e}"
            log.warning(msg)
        return msg

    def _write_position(self, positions: List[int]) -> str:
        msg: str = ""
        # Enable torque for all servos and add goal position to the bulk write parameter storage
        for i, pos in enumerate(positions):
            pos = units_to_degrees(pos)
            dxl_id = self.servos[i].id
            clipped = min(max(pos, self.servos[i].range[0]), self.servos[i].range[1])

            dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
                self.port_handler, dxl_id, self.addr_torque_enable, self.torque_enable
            )
            if dxl_comm_result != COMM_SUCCESS:
                msg += f"ERROR: {self.packet_handler.getTxRxResult(dxl_comm_result)}"
            elif dxl_error != 0:
                msg += f"ERROR: {self.packet_handler.getRxPacketError(dxl_error)}"
                raise Exception(msg)

            self.group_bulk_write.addParam(
                dxl_id, self.addr_goal_position, 4, [
                DXL_LOBYTE(DXL_LOWORD(clipped)),
                DXL_HIBYTE(DXL_LOWORD(clipped)),
                DXL_LOBYTE(DXL_HIWORD(clipped)),
                DXL_HIBYTE(DXL_HIWORD(clipped)),
            ])

        # Write goal position
        dxl_comm_result = self.group_bulk_write.txPacket()
        if dxl_comm_result != COMM_SUCCESS:
            msg += f"ERROR: {self.packet_handler.getTxRxResult(dxl_comm_result)}"
            raise Exception(msg)

        # Clear bulk write parameter storage
        self.group_bulk_write.clearParam()

    def _read_pos(self) -> List[int]:
        msg: str = ""
        # Add present position value to the bulk read parameter storage
        for i in range(self.num_servos):
            dxl_id = self.servos[i].id
            dxl_addparam_result = self.group_bulk_read.addParam(
                dxl_id, self.addr_present_position, 4
            )
            if not dxl_addparam_result:
                msg += f"ERROR: [ID:{dxl_id}] groupBulkRead addparam failed\n"
                raise Exception(msg)

        # Read present position
        dxl_comm_result = self.group_bulk_read.txRxPacket()
        if dxl_comm_result != COMM_SUCCESS:
            msg += f"ERROR: {self.packet_handler.getTxRxResult(dxl_comm_result)}\n"
            raise Exception(msg)

        # Get present position value
        positions = []
        for i in range(self.num_servos):
            dxl_id = self.servos[i].id
            dxl_present_position = self.group_bulk_read.getData(
                dxl_id, self.addr_present_position, 4
            )
            positions.append(dxl_present_position)

        # Clear bulk read parameter storage
        self.group_bulk_read.clearParam()

        return positions

    def __del__(self, *args, **kwargs) -> None:
        self.port_handler.closePort()


def test_servos(
    matplotlib: bool = False,
) -> None:
    """
    Test the Servo module.

    """
    # Set logging level
    logging.basicConfig(level=logging.DEBUG)

    # Initialize robot
    robot = Robot()

    # Initialize lists to store commanded and true positions
    commanded_positions = []
    commanded_timestamps = []

    log.debug(f"Testing move")
    for step in [
        [robot.servos[0].range[0], robot.servos[1].range[0], robot.servos[2].range[0]],
        [robot.servos[0].range[1], robot.servos[1].range[1], robot.servos[2].range[1]],
        [robot.servos[0].range[0], robot.servos[1].range[0], robot.servos[2].range[0]],
        [robot.servos[0].range[1], robot.servos[1].range[1], robot.servos[2].range[1]],
    ]:

        msg = robot.move(step)
        print(msg)
        commanded_positions.append(step)
        commanded_timestamps.append(datetime.now())
        time.sleep(2)

    # Close robot
    del robot

    # Plot commanded and true positions
    if matplotlib:
        import matplotlib.pyplot as plt

        plt.figure()
        plt.plot(commanded_timestamps, commanded_positions, label="Commanded Positions")
        plt.xlabel("Time")
        plt.ylabel("Positions")
        plt.legend()
        plt.savefig("output.png")


if __name__ == "__main__":
    test_servos()
