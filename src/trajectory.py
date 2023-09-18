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