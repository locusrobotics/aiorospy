#!/usr/bin/env python3
import asyncio
import sys
import unittest
from threading import Event

import aiounittest
import rospy
import rostest
from actionlib import ActionServer, GoalStatus
from actionlib.msg import TestAction, TestFeedback, TestGoal, TestResult
from aiorospy import AsyncActionClient
from aiorospy.helpers import deflector_shield


class TestActionClient(aiounittest.AsyncTestCase):

    @classmethod
    def setUpClass(cls):
        rospy.init_node("test_action_client", anonymous=True, disable_signals=True)

    def create_server(self, ns, goal_cb=None, cancel_cb=None, auto_start=True):
        action_server = ActionServer(ns, TestAction, goal_cb=goal_cb, cancel_cb=cancel_cb, auto_start=False)
        if auto_start:
            action_server.start()
        return action_server

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
        goal_handle = await client.send_goal(TestGoal(1))

        idx = 0
        async for feedback in goal_handle.feedback(log_period=1.0):
            print(f"feedback {idx}")
            self.assertEqual(feedback, TestFeedback(idx))
            idx += 1

        await goal_handle.wait()
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
        goal_handle = await client.send_goal(TestGoal(1))
        await goal_handle.reach_status(GoalStatus.ACTIVE, log_period=1.0)

        received_accepted.set()

        with self.assertRaises(RuntimeError):
            await goal_handle.reach_status(GoalStatus.REJECTED, log_period=1.0)

        await goal_handle.reach_status(GoalStatus.SUCCEEDED, log_period=1.0)

        with self.assertRaises(RuntimeError):
            await goal_handle.reach_status(GoalStatus.REJECTED, log_period=1.0)

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
        goal_handle = await client.send_goal(TestGoal())
        await goal_handle.reach_status(GoalStatus.ACTIVE, log_period=1.0)

        goal_handle.cancel()
        await goal_handle.reach_status(GoalStatus.PREEMPTED, log_period=1.0)

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
        await goal_handle.reach_status(GoalStatus.ACTIVE, log_period=1.0)

        client_task.cancel()
        await deflector_shield(client_task)


if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_action_client', TestActionClient, sys.argv)
