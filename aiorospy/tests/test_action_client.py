#!/usr/bin/env python3.7
import asyncio
import rospy
import rostest
import sys
import time
import unittest

from aiorospy import AsyncActionClient
from actionlib import ActionServer, GoalStatus
from actionlib.msg import TestAction, TestGoal, TestFeedback, TestResult
from threading import Event


class TestActionClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rospy.init_node("test", anonymous=True, disable_signals=True)
        cls.action_server = ActionServer("test", TestAction, lambda goal: print(goal), auto_start=False)
        cls.action_server.start()

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

        self.action_client = AsyncActionClient("test", TestAction, loop=self.loop)

    def tearDown(self):
        self.loop.close()

    def test_success_result(self):
        expected_result = TestResult(0)
        feedback_up_to = 3

        def goal_cb(goal):
            goal.set_accepted()
            for i in range(feedback_up_to):
                goal.publish_feedback(TestFeedback(i))
            goal.set_succeeded(result=expected_result)
        self.action_server.register_goal_callback(goal_cb)

        async def run_test():
            await self.action_client.wait_for_server()
            goal_handle = self.action_client.send_goal(TestGoal(1))
            i = 0
            async for feedback in goal_handle.feedback():
                self.assertEqual(feedback, TestFeedback(i))
                i += 1

            self.assertEqual(GoalStatus.SUCCEEDED, goal_handle.status)
            self.assertEqual(expected_result, goal_handle.result)

        self.loop.run_until_complete(run_test())

    def test_wait_for_result(self):
        received_accepted = Event()

        def goal_cb(goal):
            goal.set_accepted()
            received_accepted.wait()
            goal.set_succeeded(result=TestResult(0))
        self.action_server.register_goal_callback(goal_cb)

        async def run_test():
            await self.action_client.wait_for_server()
            goal_handle = self.action_client.send_goal(TestGoal(1))
            await goal_handle.wait_for_status(GoalStatus.ACTIVE)

            received_accepted.set()

            with self.assertRaises(RuntimeError):
                await goal_handle.wait_for_status(GoalStatus.REJECTED)

            await goal_handle.wait_for_status(GoalStatus.SUCCEEDED)

            with self.assertRaises(RuntimeError):
                await goal_handle.wait_for_status(GoalStatus.REJECTED)

        self.loop.run_until_complete(run_test())

if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_action_client', TestActionClient, sys.argv)
