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
MOVE_TOKEN: str = "🏃"

SYSTEM_PROMPT: str = f"""
You are an llm control unit for a robot arm called {ROBOT_TOKEN}.
"""

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

SERVOS_MSG: str = f"""
{ROBOT_TOKEN} has {len(SERVOS)} servos {SERVO_TOKEN} forming a kinematic chain
@dataclass
class Servo:
    id: int # dynamixel id for servo
    name: str # name of servo for llm use
    range: Tuple[int, int] # (min, max) position values for servos in units (0, 4095)
    desc: str # description of servo for llm use
{SERVO_TOKEN}: List[Servo] = [{"".join([str(s) for s in SERVOS])}]
"""

@dataclass
class Pose:
    name: str # name of pose for llm use
    angles: List[int] # list of int angles in degrees (0, 360)
    desc: str # description of position for llm use

POSES: Dict[str, Pose] = {
    "home" : Pose("home", [180, 211, 180], "home position or look up"),
    "forward" : Pose("forward", [180, 140, 180], "look ahead, facing forward"),
    "tilt_left" : Pose("tilt_left", [215, 130, 151], "looking forward, head tilted right"),
    "tilt_right" : Pose("tilt_right", [145, 130, 209], "looking forward, head tilted left"),
    "face_down": Pose("face_down", [180, 94, 180], "looking down, facing forward")
}

POSES_MSG: str = f"""
{ROBOT_TOKEN} can be put into {len(POSES)} different poses {POSE_TOKEN}
Each {POSE_TOKEN} contains angles in degrees for each {SERVO_TOKEN}
@dataclass
class Pose:
    name: str # name of pose for llm use
    angles: List[int] # list of int angles in degrees (0, 360)
    desc: str # description of position for llm use
{SERVO_TOKEN}: List[Servo] = [{"".join([str(s) for s in SERVOS])}]
"""

MOVE_MSG: str = f"""
The user will describe in natural language a {MOVE_TOKEN} command.
Format the command so that {ROBOT_TOKEN} can understand it.
{ROBOT_TOKEN} can accept the following commands:
{"".join([f"{pose.name}: {pose.desc}" for pose in POSES.values()])}
Return the one-word string name of the best matching pose.
"""

@dataclass
class Camera:
    id: int
    name: str
    width: int
    height: int
    desc: str

CAMERAS: List[Camera] = [
    Camera(0, "head", 1280, 480, "stereo camera located at the head, has left and right"),
    Camera(1, "chest", 640, 480, "monocular camera located at the chest pointing down"),
]

CAMERA_MSG: str = f"""
{ROBOT_TOKEN} has {len(CAMERAS)} different cameras {CAMERA_TOKEN}.
@dataclass
class Camera:
    id: int # id for camera
    name: str # name of camera for llm use
    width: int # width of image in pixels
    height: int # height of image in pixels
    desc: str # description of camera for llm use
{CAMERA_TOKEN}: List[Camera] = [{"".join([str(c) for c in CAMERAS])}]
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
        cameras: List[Camera] = CAMERAS,
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
        self.cameras = cameras # List of Camera objects to control

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

    def move(
        self,
        goal_positions: List[int],
        epsilon: int = 10, # degrees
        timeout: timedelta = timedelta(seconds=1), #timeout
    ) -> str:
        msg: str = ""
        start_time = time.time()
        try:
            while True:
                elapsed_time = time.time() - start_time
                msg += f"{ROBOT_TOKEN} commanded to position {goal_positions}\n"
                self._write_position(goal_positions)
                true_positions = self._read_pos()
                msg += f"{ROBOT_TOKEN} at position {true_positions}\n"
                if epsilon > sum(abs(true_positions[i] - goal_positions[i]) for i in range(len(goal_positions))):
                    msg += f"{MOVE_TOKEN} succeeded in {elapsed_time} seconds.\n"
                    break
                if elapsed_time > timeout.total_seconds():
                    msg += f"{MOVE_TOKEN} timed out after {elapsed_time} seconds.\n"
                    break 
        except Exception as e:
            msg += f"{MOVE_TOKEN} failed with exception {e}"
            log.warning(msg)
        return msg

    def _write_position(self, positions: List[int]) -> str:
        msg: str = ""
        # Enable torque for all servos and add goal position to the bulk write parameter storage
        for i, pos in enumerate(positions):
            pos = degrees_to_units(pos)
            dxl_id = self.servos[i].id
            clipped = min(max(pos, self.servos[i].range[0]), self.servos[i].range[1])

            dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
                self.port_handler, dxl_id, self.addr_torque_enable, self.torque_enable
            )
            if dxl_comm_result != COMM_SUCCESS:
                msg += f"ERROR: {self.packet_handler.getTxRxResult(dxl_comm_result)}"
                raise Exception(msg)
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
            positions.append(units_to_degrees(dxl_present_position))

        # Clear bulk read parameter storage
        self.group_bulk_read.clearParam()

        return positions
    
    def _disable_torque(self) -> None:
        for servo in self.servos:
            dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
                self.port_handler, servo.id, self.addr_torque_enable, self.torque_disable
            )
            if dxl_comm_result != COMM_SUCCESS:
                log.error(f"ERROR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
            elif dxl_error != 0:
                log.error(f"ERROR: {self.packet_handler.getRxPacketError(dxl_error)}")

    def __del__(self, *args, **kwargs) -> None:
        self.move(self.poses["home"].angles)
        self._disable_torque()
        self.port_handler.closePort()

def move_with_prompt(
    robot: Robot,
    llm_func: callable,
    raw_move_str: int = "home",
    system_msg: str = SYSTEM_PROMPT,
    move_msg: str = MOVE_MSG,
) -> str:
    msg: str = ""
    desired_pose_name = llm_func(
            max_tokens=8,
            messages=[
                {"role": "system", "content": f"{system_msg}\n{move_msg}"},
                {"role": "user", "content": raw_move_str},
            ]
    )
    msg += f"{MOVE_TOKEN} commanded pose is {desired_pose_name}\n"
    desired_pose = POSES.get(desired_pose_name, None)
    if desired_pose is not None:
        return robot.move(desired_pose.angles)
    else:
        msg += f"ERROR: {desired_pose_name} is not a valid pose.\n"
        return msg

def test_servos() -> None:
    log.setLevel(logging.DEBUG)
    log.debug("Testing move")
    robot = Robot()
    for pose in robot.poses.values():
        msg = robot.move(pose.angles)
        print(msg)
        time.sleep(1)
    del robot

def test_servos_llm() -> None:
    log.setLevel(logging.DEBUG)
    log.debug("Testing move with prompt")
    robot = Robot()
    for raw_move_str in [
        "go to the home position",
        "check on your left",
        "bogie on your right",
        "what is on the floor",
    ]:
        msg = move_with_prompt(robot, raw_move_str=raw_move_str)
        print(msg)
        time.sleep(1)
    del robot

def test_camera() -> None:
    pass

if __name__ == "__main__":
    test_servos()
    test_servos_llm()
    test_camera()
