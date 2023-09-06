from typing import List, Tuple

# In-context dataset for human-head-like trajectories.
traj_hooman_incontext: List[Tuple[str, str]] = [
  ("nod", "up and down motion"),
  ("shake", "side to side motion"),
  ("look left", "turn head to the left"),
  ("look right", "turn head to the right"),
  ("tilting", "side tilt"),
  ("jutting", "forward thrust"),
  ("retracting", "pulling back"),
  ("dropping", "lowering down"),
  ("raising", "lifting up"),
  ("rolling", "circular motion"),
  ("turning away", "rotation away"),
  ("bobbing", "rapid up and down or side to side"),
  ("cocking", "slight sideways tilt"),
  ("pecking", "quick forward motion"),
  ("rubbing", "hand over head"),
  ("patting", "hand tapping"),
  ("resting on hand", "head on hand"),
  ("snapping", "quick upward or sideways"),
  ("whipping", "rapid turn"),
  ("swaying", "slow side to side"),
  ("wagging", "exaggerated side to side"),
  ("pivoting", "rotating horizontally or vertically"),
  ("pressing", "pushing against something")
]
