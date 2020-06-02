#!/usr/bin/env python3
import asyncio
import sys
import unittest

import aiounittest
import janus
import rospy
import rostest
from actionlib import ActionClient as SyncActionClient
from actionlib import CommState, GoalStatus
from actionlib.msg import TestAction, TestGoal, TestResult
from aiorospy import AsyncActionServer
from aiorospy.helpers import deflector_shield


class TestActionServer(aiounittest.AsyncTestCase):

    @classmethod
    def setUpClass(cls):
        rospy.init_node("test_action_server", anonymous=True, disable_signals=True)

    async def wait_for_status(self, goal_handle, status):
        while goal_handle.get_goal_status() != status:
            await asyncio.sleep(0.1)

    async def wait_for_result(self, goal_handle):
        while goal_handle.get_comm_state() != CommState.DONE:
            await asyncio.sleep(0.1)

    async def test_goal_succeeded(self):
        magic_value = 5

        async def goal_coro(goal_handle):
            goal_handle.set_accepted()
            goal_handle.set_succeeded(result=TestResult(goal_handle.get_goal().goal))

        client = SyncActionClient("test_goal_succeeded", TestAction)
        server = AsyncActionServer(client.ns, TestAction, coro=goal_coro)
        server_task = asyncio.ensure_future(server.start())

        await asyncio.get_event_loop().run_in_executor(None, client.wait_for_server)
        goal_handle = client.send_goal(TestGoal(magic_value))

        await self.wait_for_result(goal_handle)

        self.assertEqual(goal_handle.get_goal_status(), GoalStatus.SUCCEEDED)
        self.assertEqual(goal_handle.get_result().result, magic_value)

        server_task.cancel()
        await deflector_shield(server_task)

    async def test_goal_canceled_from_client(self):
        async def goal_coro(goal_handle):
            try:
                goal_handle.set_accepted()
                await asyncio.sleep(1000000)
            except asyncio.CancelledError:
                goal_handle.set_canceled()
                raise
            goal_handle.set_succeeded()

        client = SyncActionClient("test_goal_canceled_from_client", TestAction)
        server = AsyncActionServer(client.ns, TestAction, coro=goal_coro)
        server_task = asyncio.ensure_future(server.start())

        await asyncio.get_event_loop().run_in_executor(None, client.wait_for_server)
        goal_handle = client.send_goal(TestGoal())

        await self.wait_for_status(goal_handle, GoalStatus.ACTIVE)

        goal_handle.cancel()

        await self.wait_for_status(goal_handle, GoalStatus.PREEMPTED)
        self.assertEquals(goal_handle.get_goal_status(), GoalStatus.PREEMPTED)

        server_task.cancel()
        await deflector_shield(server_task)

    async def test_goal_canceled_from_server(self):
        queue = janus.Queue()

        async def goal_coro(goal_handle):
            queue.sync_q.put_nowait(goal_handle)
            try:
                goal_handle.set_accepted()
                await asyncio.sleep(1000000)
            except asyncio.CancelledError:
                goal_handle.set_canceled()
                raise
            goal_handle.set_succeeded()

        client = SyncActionClient("test_goal_canceled_from_server", TestAction)
        server = AsyncActionServer(client.ns, TestAction, coro=goal_coro)
        server_task = asyncio.ensure_future(server.start())

        await asyncio.get_event_loop().run_in_executor(None, client.wait_for_server)
        goal_handle = client.send_goal(TestGoal())

        await self.wait_for_status(goal_handle, GoalStatus.ACTIVE)

        server_goal_handle = await queue.async_q.get()
        await server.cancel(server_goal_handle)

        await self.wait_for_status(goal_handle, GoalStatus.PREEMPTED)
        self.assertEquals(goal_handle.get_goal_status(), GoalStatus.PREEMPTED)

        server_task.cancel()
        await deflector_shield(server_task)

    async def test_goal_exception(self):
        async def goal_coro(goal_handle):
            goal_handle.set_accepted()
            raise RuntimeError()

        client = SyncActionClient("test_goal_aborted", TestAction)
        server = AsyncActionServer(client.ns, TestAction, coro=goal_coro)
        server_task = asyncio.ensure_future(server.start())

        await asyncio.get_event_loop().run_in_executor(None, client.wait_for_server)
        goal_handle = client.send_goal(TestGoal())

        await self.wait_for_status(goal_handle, GoalStatus.ABORTED)
        self.assertEquals(goal_handle.get_goal_status(), GoalStatus.ABORTED)

        with self.assertRaises(RuntimeError):
            await deflector_shield(server_task)

    async def test_server_simple(self):
        event = asyncio.Event()

        async def goal_coro(goal_handle):
            delay = goal_handle.get_goal().goal
            try:
                if event.is_set():
                    raise RuntimeError(f"Event wasn't cleared by another goal, bail!")
                event.set()
                goal_handle.set_accepted()

                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                event.clear()
                goal_handle.set_canceled()
                raise

            event.clear()
            goal_handle.set_succeeded(result=TestResult(delay))

        client = SyncActionClient("test_server_simple", TestAction)
        server = AsyncActionServer(client.ns, TestAction, coro=goal_coro, simple=True)
        server_task = asyncio.ensure_future(server.start())

        await asyncio.get_event_loop().run_in_executor(None, client.wait_for_server)

        handles = []
        for i in range(10):
            handle = client.send_goal(TestGoal(1000000))
            await self.wait_for_status(handle, GoalStatus.ACTIVE)
            handles.append(handle)

        last_handle = client.send_goal(TestGoal(0))
        await self.wait_for_status(last_handle, GoalStatus.SUCCEEDED)

        for handle in handles:
            self.assertEqual(handle.get_goal_status(), GoalStatus.PREEMPTED)
        self.assertEqual(last_handle.get_goal_status(), GoalStatus.SUCCEEDED)

        server_task.cancel()
        await deflector_shield(server_task)


if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_action_server', TestActionServer, sys.argv)
