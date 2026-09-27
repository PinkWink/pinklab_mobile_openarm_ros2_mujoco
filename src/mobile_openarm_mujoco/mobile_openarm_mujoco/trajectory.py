"""Validation and interpolation independent of ROS action scheduling."""

import math
import numpy as np

LIMIT_TOLERANCE = 0.02  # rad. MoveIt 의 계획용 한계가 URDF 보다 0.01 넓다(joint_limits.yaml); 그보다 커야 한다. 액추에이터 ctrlrange 가 어차피 클램프한다.


def seconds(duration):
    return duration.sec + duration.nanosec * 1e-9


def validate_trajectory(trajectory, names, limits, now):
    if set(trajectory.joint_names) != set(names) or len(trajectory.joint_names) != len(
        names
    ):
        raise ValueError("Joint names must match this controller exactly")
    if not trajectory.points:
        raise ValueError("Trajectory has no points")
    header = seconds(trajectory.header.stamp)
    if header and header < now - 0.1:
        raise ValueError("Trajectory header is in the past")
    previous = -1.0
    for p in trajectory.points:
        t = seconds(p.time_from_start)
        if not math.isfinite(t) or t < 0 or t <= previous:
            raise ValueError(
                "Trajectory times must be nonnegative and strictly increasing"
            )
        previous = t
        if len(p.positions) != len(names):
            raise ValueError("A position is required for every joint")
        for values in [p.positions, p.velocities, p.accelerations, p.effort]:
            if values and (
                len(values) != len(names) or not all(math.isfinite(x) for x in values)
            ):
                raise ValueError("Malformed or nonfinite trajectory values")
        for n, q in zip(trajectory.joint_names, p.positions):
            lo, hi = limits[n]
            # IK solutions often land exactly on a limit with floating-point overshoot;
            # tolerate a milliradian, the position actuator's ctrlrange clamps anyway.
            if not lo - LIMIT_TOLERANCE <= q <= hi + LIMIT_TOLERANCE:
                raise ValueError(f"{n}: {q} outside [{lo}, {hi}]")
    return True


class Trajectory:
    def __init__(self, trajectory, current):
        self.times = np.array([seconds(p.time_from_start) for p in trajectory.points])
        self.positions = np.array([p.positions for p in trajectory.points])
        self.velocities = (
            np.array([p.velocities for p in trajectory.points])
            if all(p.velocities for p in trajectory.points)
            else None
        )
        if self.times[0] > 0:
            self.times = np.r_[0.0, self.times]
            self.positions = np.vstack([current, self.positions])
            if self.velocities is not None:
                self.velocities = np.vstack([np.zeros(len(current)), self.velocities])

    def sample(self, t):
        if t <= self.times[0]:
            return self.positions[0].copy()
        if t >= self.times[-1]:
            return self.positions[-1].copy()
        i = np.searchsorted(self.times, t, side="right") - 1
        dt = self.times[i + 1] - self.times[i]
        u = (t - self.times[i]) / dt
        a, b = self.positions[i : i + 2]
        if self.velocities is None:
            return a + (b - a) * u
        va, vb = self.velocities[i : i + 2]
        return (
            (2 * u**3 - 3 * u**2 + 1) * a
            + (u**3 - 2 * u**2 + u) * dt * va
            + (-2 * u**3 + 3 * u**2) * b
            + (u**3 - u**2) * dt * vb
        )
