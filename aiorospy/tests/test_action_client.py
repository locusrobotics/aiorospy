# from mock import patch

# from aiohttp import web
# from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop, make_mocked_coro, unused_port
# from async_exec.api import HttpClient

import asyncio
import rospy
import rostest
import sys
import time
import unittest

from aiorospy import AsyncActionClient
from actionlib import ActionServer, GoalStatus
from actionlib.msg import TestAction, TestGoal, TestFeedback, TestResult

class TestActionClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rospy.init_node("test", anonymous=True, disable_signals=True)
        cls.action_server = ActionServer("test", TestAction, lambda goal: print(goal), auto_start=False)
        cls.action_server.start()

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

        self.action_client = AsyncActionClient("test", TestAction)

    def tearDown(self):
        self.loop.close()

    def test_naive(self):
        expected_result = TestResult(0)
        feedback_up_to = 3

        def goal_cb(goal):
            goal.set_accepted()
            for i in range(feedback_up_to):
                goal.publish_feedback(TestFeedback(i))
            goal.set_succeeded(result=expected_result)

        self.action_server.register_goal_callback(goal_cb)

        async def run_test():
            goal_handle = self.action_client.send_goal(TestGoal(1), loop=asyncio.get_running_loop())
            i = 0
            async for feedback in goal_handle.feedback():
                self.assertEqual(feedback, TestFeedback(i))
                i += 1

            self.assertEqual(GoalStatus.SUCCEEDED, goal_handle.status())
            self.assertEqual(expected_result, await goal_handle.result())

        self.loop.run_until_complete(run_test())

if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_action_client', TestActionClient, sys.argv)
