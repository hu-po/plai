from typing import List, Tuple

class Trajectory:
    
    num_servos: int = 3
    keyframe_delimiter: str = ';'
    servo_delimiter: str = ','

    def __init__(
        self,
        trajectory: List[List[int]] = [[0, 0, 0], [360, 360, 360]],
        description: str = '',
        num_keyframes: int = 2,
    ):
        self.trajectory = trajectory
        self.description = description
        self.num_keyframes = num_keyframes


    def __str__(self):
        _trajectory = ''
        for keyframe in self.trajectory:
            for servo in keyframe:
                _trajectory += f'{servo}{self.servo_delimiter}'
            _trajectory += self.keyframe_delimiter
        return _trajectory

    @classmethod
    def parse(cls, trajectory_string: str):
        _trajectory = []
        for trajectory_str in trajectory_string.split(cls.keyframe_delimiter):
            _servos = []
            for servo_str in trajectory_str.split(cls.servo_delimiter):
                _servos.append(int(servo_str))
            if len(_servos) != cls.num_servos:
                raise ValueError(f"Each keyframe must have exactly {cls.num_servos} servos")
            _trajectory.append(_servos)
        return cls(
            trajectory = _trajectory,
            num_keyframes = len(_trajectory),
        )

def gpt_trajectory(
    trajectory_description: str,
    num_keyframes: int = 4,
    num_servos: int = 3,
    keyframe_delimiter: str = ";",
    servo_delimiter: str = ",",
    min_value: int = 0,
    max_value: int = 360,
) -> List[Tuple[int, int]]:
    _messages = [
        {
            "role": "system",
            "content": " ".join(
                [
                    "Output a trajectory based on a string description of a trajectory and a number of keyframes.",
                    f"You output trajectories for a {num_servos}DoF robot arm.",
                    f"A trajectory is a sequence of keyframes.",
                    f"Each keyframe represents {num_servos} integer degree values for each servo between {min_value} and {max_value}.",
                    f"The delimiter used for the trajectory is {keyframe_delimiter}",
                    f"The delimiter used for the servo values is {servo_delimiter}",
                ]
            ),
        },
        {
            "role": "user",
            "content": "keyframes: 3, description: min, max, min",
        },
        {
            "role": "assistant",
            "content": f"{servo_delimiter.join([str(min_value)] * num_servos)}{keyframe_delimiter}{servo_delimiter.join([str(max_value)] * num_servos)}{keyframe_delimiter}{servo_delimiter.join([str(min_value)] * num_servos)}",
        },
        {
            "role": "user",
            "content": "keyframes: 2, description: zero to halfway",
        },
        {
            "role": "assistant",
            "content": f"{servo_delimiter.join([str(min_value)] * num_servos)}{keyframe_delimiter}{servo_delimiter.join([str(max_value//2)] * num_servos)}",
        },
        {
            "role": "user",
            "content": f"keyframes: {num_keyframes}, description: {trajectory_description}",
        },
    ]
    reply = gpt_text(messages=_messages)
    trajectory = Trajectory.parse(reply)
    return trajectory

