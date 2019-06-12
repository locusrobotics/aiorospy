#!/usr/bin/env python3.7
import asyncio
import sys
import unittest

import aiounittest
import rospy
import rostest
from actionlib import ActionClient as SyncActionClient
from actionlib import GoalStatus
from actionlib.msg import TestAction, TestGoal, TestResult
from aiorospy import AsyncActionServer


class TestActionServer(aiounittest.AsyncTestCase):

    @classmethod
    def setUpClass(cls):
        rospy.init_node("test_action_server", anonymous=True, disable_signals=True)

    async def wait_for_status(self, goal_handle, status):
        while goal_handle.get_goal_status() != status:
            await asyncio.sleep(0.1)

    async def test_goal_succeeded(self):
        magic_value = 5

        async def goal_coro(goal_handle):
            goal_handle.set_accepted()
            goal_handle.set_succeeded(result=TestResult(goal_handle.get_goal().goal))

        client = SyncActionClient("test_goal_succeeded", TestAction)
        server = AsyncActionServer(client.ns, TestAction, coro=goal_coro)
        server_task = asyncio.create_task(server.start())

        await asyncio.get_event_loop().run_in_executor(None, client.wait_for_server)
        goal_handle = client.send_goal(TestGoal(magic_value))

        await self.wait_for_status(goal_handle, GoalStatus.SUCCEEDED)

        self.assertEqual(goal_handle.get_goal_status(), GoalStatus.SUCCEEDED)
        self.assertEqual(goal_handle.get_result().result, magic_value)

        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    async def test_goal_canceled(self):
        async def goal_coro(goal_handle):
            try:
                goal_handle.set_accepted()
                await asyncio.sleep(1009000)
            except asyncio.CancelledError:
                goal_handle.set_canceled()
                raise

        client = SyncActionClient("test_goal_canceled", TestAction)
        server = AsyncActionServer(client.ns, TestAction, coro=goal_coro)
        server_task = asyncio.create_task(server.start())

        await asyncio.get_event_loop().run_in_executor(None, client.wait_for_server)
        goal_handle = client.send_goal(TestGoal())

        await self.wait_for_status(goal_handle, GoalStatus.ACTIVE)

        goal_handle.cancel()

        await self.wait_for_status(goal_handle, GoalStatus.PREEMPTED)
        self.assertEquals(goal_handle.get_goal_status(), GoalStatus.PREEMPTED)

        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    async def test_goal_exception(self):
        async def goal_coro(goal_handle):
            goal_handle.set_accepted()
            raise RuntimeError()

        client = SyncActionClient("test_goal_aborted", TestAction)
        server = AsyncActionServer(client.ns, TestAction, coro=goal_coro)
        server_task = asyncio.create_task(server.start())

        await asyncio.get_event_loop().run_in_executor(None, client.wait_for_server)
        goal_handle = client.send_goal(TestGoal())

        await self.wait_for_status(goal_handle, GoalStatus.ABORTED)
        self.assertEquals(goal_handle.get_goal_status(), GoalStatus.ABORTED)

        with self.assertRaises(RuntimeError):
            await server_task


if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_action_server', TestActionServer, sys.argv)
