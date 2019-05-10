#!/usr/bin/env python3.7
import asyncio
import rospy
import rostest
import sys
import unittest

from aiorospy import AsyncActionServer
from actionlib import ActionClient as SyncActionClient, GoalStatus
from actionlib.msg import TestAction, TestGoal, TestResult


class TestActionServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rospy.init_node("test_action_server", anonymous=True, disable_signals=True)

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

    def tearDown(self):
        self.loop.close()

    async def wait_for_status(self, goal_handle, status):
        while goal_handle.get_goal_status() != status:
            print(f"status {GoalStatus.to_string(goal_handle.get_goal_status())}")
            await asyncio.sleep(0.1)

    def test_goal_succeeded(self):
        magic_value = 5

        async def goal_coro(goal_handle):
            goal_handle.set_accepted()
            goal_handle.set_succeeded(result=TestResult(goal_handle.get_goal().goal))

        client = SyncActionClient("test_goal_succeeded", TestAction)
        server = AsyncActionServer(client.ns, TestAction, coro=goal_coro, loop=self.loop)

        client.wait_for_server()
        goal_handle = client.send_goal(TestGoal(magic_value))

        self.loop.run_until_complete(
            asyncio.wait_for(self.wait_for_status(goal_handle, GoalStatus.SUCCEEDED), timeout=1))
        self.assertEqual(goal_handle.get_goal_status(), GoalStatus.SUCCEEDED)
        self.assertEqual(goal_handle.get_result().result, magic_value)

    def test_goal_canceled(self):
        async def goal_coro(goal_handle):
            with self.assertRaises(asyncio.CancelledError) as cm:
                try:
                    goal_handle.set_accepted()
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    goal_handle.set_canceled()
                    raise
            raise cm.exception

        client = SyncActionClient("test_goal_canceled", TestAction)
        server = AsyncActionServer(client.ns, TestAction, coro=goal_coro, loop=self.loop)

        client.wait_for_server()
        goal_handle = client.send_goal(TestGoal())

        self.loop.run_until_complete(
            asyncio.wait_for(self.wait_for_status(goal_handle, GoalStatus.ACTIVE), timeout=1))

        goal_handle.cancel()

        self.loop.run_until_complete(
            asyncio.wait_for(self.wait_for_status(goal_handle, GoalStatus.PREEMPTED), timeout=1))
        self.assertEquals(goal_handle.get_goal_status(), GoalStatus.PREEMPTED)


if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_action_server', TestActionServer, sys.argv)
