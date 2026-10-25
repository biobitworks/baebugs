"""Run from the arm/ folder: python -m unittest test_motion"""
import unittest

import motion
from motion import Arm, MissedGrab, MissingPose, PracticeFollower
from teach import poses_needed, practice_poses


class Recorder(PracticeFollower):
    """Stand-in follower that also keeps every goal it was sent."""

    def __init__(self):
        super().__init__()
        self.sent = []

    def send_action(self, action):
        self.sent.append({k.removesuffix(".pos"): v for k, v in action.items()})
        return super().send_action(action)


def make_arm(grip_on_object=True):
    layout = motion.load_layout()
    robot = Recorder()
    robot.object_at = 60.0 if grip_on_object else None
    return Arm(robot, layout, practice_poses(layout), realtime=False, log=lambda *_: None), robot


class PosesTest(unittest.TestCase):
    def test_routines_ask_for_every_slot_and_dump_pose(self):
        names = motion.required_poses(motion.load_layout())
        for name in ["rest", "gripper/open", "gripper/closed", "rig/carry", "storage/carry",
                     "rig/top/front", "rig/top/in", "storage/bottom/in", "dish/grip", "pour/tilt"]:
            self.assertIn(name, names)

    def test_transfer_needs_both_carry_poses(self):
        layout = motion.load_layout()
        needed = poses_needed(layout, motion.transfer_steps(layout, "rig/top", "storage/top"))
        self.assertIn("rig/carry", needed)
        self.assertIn("storage/carry", needed)

    def test_missing_pose_stops_with_a_clear_message(self):
        arm, _ = make_arm()
        del arm.poses["rig/top/in"]
        with self.assertRaisesRegex(MissingPose, "save rig/top/in"):
            arm.run(motion.pick_steps(arm.layout, "rig/top"))


class MoveTest(unittest.TestCase):
    def test_moves_never_exceed_the_speed_and_end_on_target(self):
        arm, robot = make_arm()
        arm.move_to("rig/top/front", "slow")
        limit = arm.layout["speeds"]["slow"] / motion.RATE_HZ
        goals = robot.sent
        for a, b in zip(goals, goals[1:]):
            for j in motion.ARM_JOINTS:
                self.assertLessEqual(abs(b[j] - a[j]), limit * 1.05)
        for j in motion.ARM_JOINTS:
            self.assertAlmostEqual(robot.position[j], arm.poses["rig/top/front"][j])


class RoutineTest(unittest.TestCase):
    def test_turns_between_sides_only_at_the_carry_poses(self):
        arm, _ = make_arm()
        arm.run(motion.transfer_steps(arm.layout, "rig/top", "storage/top"))
        side = lambda name: name.split("/")[0]
        for a, b in zip(arm.visited, arm.visited[1:]):
            if side(a) != side(b):
                self.assertEqual((a, b), ("rig/carry", "storage/carry"))
        self.assertEqual(arm.visited[-1], "storage/carry")

    def test_backs_straight_out_of_a_slot(self):
        arm, _ = make_arm()
        arm.run(motion.pick_steps(arm.layout, "rig/middle"))
        i = arm.visited.index("rig/middle/in")
        self.assertEqual(arm.visited[i - 1:i + 2], ["rig/middle/front", "rig/middle/in", "rig/middle/front"])

    def test_missed_grab_opens_backs_out_and_stops(self):
        arm, robot = make_arm(grip_on_object=False)
        with self.assertRaises(MissedGrab):
            arm.run(motion.transfer_steps(arm.layout, "rig/top", "storage/top"))
        self.assertEqual(arm.visited[-1], "rig/top/front")
        self.assertAlmostEqual(robot.position["gripper"], arm.poses["gripper/open"]["gripper"])
        self.assertNotIn("storage/carry", arm.visited)

    def test_dump_grabs_pours_and_puts_the_dish_back(self):
        arm, _ = make_arm()
        arm.run(motion.dump_steps(arm.layout))
        self.assertLess(arm.visited.index("pour/tilt"), arm.visited.index("dish/grip", 2))
        self.assertEqual(arm.visited[-1], "dish/above")


if __name__ == "__main__":
    unittest.main()
