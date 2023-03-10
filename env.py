"""
    Environment for RL

    Following

    https://gymnasium.farama.org/tutorials/gymnasium_basics/environment_creation/#sphx-glr-tutorials-gymnasium-basics-environment-creation-py

"""

import numpy as np
import pygame

import gymnasium as gym
from gymnasium import spaces


class PlaiEnv(gym.Env):
    metadata = {'render.modes': ['human', 'rgb_array'], "render_fps": 4}

    def __init__(self,
                 render_mode=None,
    ):
        self.observation_space = {
            "image": spaces.Box(low=0, high=255, shape=(100, 100, 3), dtype=np.uint8),
            "position": spaces.Box(low=0, high=100, shape=(2,), dtype=np.uint8),
            "velocity": spaces.Box(low=0, high=100, shape=(2,), dtype=np.uint8),
        }
        self.action_space = spaces.Continuous(2)
        assert render_mode is None or render_mode in self.metadata["render_modes"]
        self.render_mode = render_mode
        self.window = None
        self.clock = None

        # Create servo context
        # Create camera and model context



    def _get_obs(self):
        # used in step and reset
        return {
            "image": self._image_obs,
            "position": self._position_obs,
            "velocity": self._velocity_obs,
        }
    
    def _get_info(self):
        # used in step and reset
        return {}

    def reset(self, seed=None, options=None):
        # We need the following line to seed self.np_random
        super().reset(seed=seed)

        
        # Set servos to initial position
        self._position_obs = np.zeros(2)

        

        observation = self._get_obs()
        info = self._get_info()

        if self.render_mode == "human":
            self._render_frame()

        return observation, info
