#!/usr/bin/env python3
import asyncio
import sys
from threading import Event

import aiounittest
import rospy
import rostest
from actionlib import ActionServer, GoalStatus
from actionlib.msg import TestAction, TestFeedback, TestGoal, TestResult
from aiorospy import AsyncActionClient
from aiorospy.helpers import deflector_shield

WAIT_TIMEOUT = 5.0
MAX_RETRIES = 3


class TestActionClient(aiounittest.AsyncTestCase):

    @classmethod
    def setUpClass(cls):
        rospy.init_node("test_action_client", anonymous=True, disable_signals=True)

    def create_server(self, ns, goal_cb=None, cancel_cb=None, auto_start=True):
        action_server = ActionServer(ns, TestAction, goal_cb=goal_cb, cancel_cb=cancel_cb, auto_start=False)
        if auto_start:
            action_server.start()
        return action_server

    async def retry_on_timeout(self, fn):
        """Retry an async callable up to MAX_RETRIES times on TimeoutError.

        Under heavy CPU load the ROS spinner thread can be starved,
        causing goal delivery or status propagation to exceed
        WAIT_TIMEOUT.  Retrying the send+wait cycle handles this
        transient condition without masking real failures.
        """
        for attempt in range(MAX_RETRIES):
            try:
                return await fn()
            except asyncio.TimeoutError:
                if attempt == MAX_RETRIES - 1:
                    raise

    async def test_success_result(self):
        expected_result = TestResult(0)
        feedback_up_to = 3

        def goal_cb(goal_handle):
            goal_handle.set_accepted()
            for idx in range(feedback_up_to):
                goal_handle.publish_feedback(TestFeedback(idx))
            goal_handle.set_succeeded(result=expected_result)

        server = self.create_server("test_success_result", goal_cb)
        client = AsyncActionClient(server.ns, TestAction)
        client_task = asyncio.ensure_future(client.start())

        await client.wait_for_server()

        async def send_and_wait():
            gh = await client.send_goal(TestGoal(1))
            idx = 0
            async for feedback in gh.feedback(log_period=1.0):
                self.assertEqual(feedback, TestFeedback(idx))
                idx += 1
            await gh.wait()
            return gh

        async def attempt():
            return await asyncio.wait_for(send_and_wait(), timeout=WAIT_TIMEOUT)

        goal_handle = await self.retry_on_timeout(attempt)

        self.assertEqual(goal_handle.status, GoalStatus.SUCCEEDED)
        self.assertEqual(expected_result, goal_handle.result)

        client_task.cancel()
        await deflector_shield(client_task)

    async def test_wait_for_result(self):
        received_accepted = Event()

        def goal_cb(goal_handle):
            goal_handle.set_accepted()
            received_accepted.wait()
            goal_handle.set_succeeded(result=TestResult(0))

        server = self.create_server("test_wait_for_result", goal_cb)
        client = AsyncActionClient(server.ns, TestAction)
        client_task = asyncio.ensure_future(client.start())

        await client.wait_for_server()

        async def send_and_reach_active():
            gh = await client.send_goal(TestGoal(1))
            await asyncio.wait_for(
                gh.reach_status(GoalStatus.ACTIVE, log_period=1.0),
                timeout=WAIT_TIMEOUT)
            return gh

        goal_handle = await self.retry_on_timeout(send_and_reach_active)

        received_accepted.set()

        with self.assertRaises(RuntimeError):
            await asyncio.wait_for(
                goal_handle.reach_status(GoalStatus.REJECTED, log_period=1.0),
                timeout=WAIT_TIMEOUT)

        await asyncio.wait_for(
            goal_handle.reach_status(GoalStatus.SUCCEEDED, log_period=1.0),
            timeout=WAIT_TIMEOUT)

        with self.assertRaises(RuntimeError):
            await asyncio.wait_for(
                goal_handle.reach_status(GoalStatus.REJECTED, log_period=1.0),
                timeout=WAIT_TIMEOUT)

        client_task.cancel()
        await deflector_shield(client_task)

    async def test_cancel(self):
        def goal_cb(goal_handle):
            goal_handle.set_accepted()

        def cancel_cb(goal_handle):
            goal_handle.set_canceled()

        server = self.create_server("test_cancel", goal_cb, cancel_cb)
        client = AsyncActionClient(server.ns, TestAction)
        client_task = asyncio.ensure_future(client.start())

        await client.wait_for_server()

        async def send_and_reach_active():
            gh = await client.send_goal(TestGoal())
            await asyncio.wait_for(
                gh.reach_status(GoalStatus.ACTIVE, log_period=1.0),
                timeout=WAIT_TIMEOUT)
            return gh

        goal_handle = await self.retry_on_timeout(send_and_reach_active)

        goal_handle.cancel()
        await asyncio.wait_for(
            goal_handle.reach_status(GoalStatus.PREEMPTED, log_period=1.0),
            timeout=WAIT_TIMEOUT)

        client_task.cancel()
        await deflector_shield(client_task)

    async def test_ensure(self):
        def goal_cb(goal_handle):
            goal_handle.set_accepted()

        server = self.create_server("test_ensure", goal_cb, auto_start=False)
        client = AsyncActionClient(server.ns, TestAction)
        client_task = asyncio.ensure_future(client.start())

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(client.ensure_goal(TestGoal(), resend_timeout=0.1), timeout=1)

        server.start()

        goal_handle = await client.ensure_goal(TestGoal(), resend_timeout=0.1)
        await asyncio.wait_for(
            goal_handle.reach_status(GoalStatus.ACTIVE, log_period=1.0),
            timeout=WAIT_TIMEOUT)

        client_task.cancel()
        await deflector_shield(client_task)


if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_action_client', TestActionClient, sys.argv)
