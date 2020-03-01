#!/usr/bin/env python3.7
import asyncio
import sys
import unittest
from threading import Event

import aiostream
import aiounittest
import rospy
import rostest
from actionlib import ActionServer, GoalStatus
from actionlib.msg import TestAction, TestFeedback, TestGoal, TestResult
from aiorospy import AsyncActionClient


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
        client_task = asyncio.create_task(client.start())

        await client.wait_for_server()
        goal_handle = await client.send_goal(TestGoal(1))
        async for idx, feedback in aiostream.stream.enumerate(goal_handle.feedback()):
            self.assertEqual(feedback, TestFeedback(idx))

        self.assertEqual(GoalStatus.SUCCEEDED, goal_handle.status)
        self.assertEqual(expected_result, goal_handle.result)

        client_task.cancel()
        try:
            await client_task
        except asyncio.CancelledError:
            pass

    async def test_wait_for_result(self):
        received_accepted = Event()

        def goal_cb(goal_handle):
            goal_handle.set_accepted()
            received_accepted.wait()
            goal_handle.set_succeeded(result=TestResult(0))

        server = self.create_server("test_wait_for_result", goal_cb)
        client = AsyncActionClient(server.ns, TestAction)
        client_task = asyncio.create_task(client.start())

        await client.wait_for_server()
        goal_handle = await client.send_goal(TestGoal(1))
        await goal_handle.reach_status(GoalStatus.ACTIVE)

        received_accepted.set()

        with self.assertRaises(RuntimeError):
            await goal_handle.reach_status(GoalStatus.REJECTED)

        await goal_handle.reach_status(GoalStatus.SUCCEEDED)

        with self.assertRaises(RuntimeError):
            await goal_handle.reach_status(GoalStatus.REJECTED)

        client_task.cancel()
        try:
            await client_task
        except asyncio.CancelledError:
            pass

    async def test_cancel(self):
        def goal_cb(goal_handle):
            goal_handle.set_accepted()

        def cancel_cb(goal_handle):
            goal_handle.set_canceled()

        server = self.create_server("test_cancel", goal_cb, cancel_cb)
        client = AsyncActionClient(server.ns, TestAction)
        client_task = asyncio.create_task(client.start())

        await client.wait_for_server()
        goal_handle = await client.send_goal(TestGoal())
        await goal_handle.reach_status(GoalStatus.ACTIVE)

        await goal_handle.cancel()
        await goal_handle.reach_status(GoalStatus.PREEMPTED)

        client_task.cancel()
        try:
            await client_task
        except asyncio.CancelledError:
            pass

    async def test_ensure(self):
        def goal_cb(goal_handle):
            goal_handle.set_accepted()

        server = self.create_server("test_ensure", goal_cb, auto_start=False)
        client = AsyncActionClient(server.ns, TestAction)
        client_task = asyncio.create_task(client.start())

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(client.ensure_goal(TestGoal(), resend_timeout=0.1), timeout=1)

        server.start()

        goal_handle = await client.ensure_goal(TestGoal(), resend_timeout=0.1)
        await goal_handle.reach_status(GoalStatus.ACTIVE)

        client_task.cancel()
        try:
            await client_task
        except asyncio.CancelledError:
            pass


if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_action_client', TestActionClient, sys.argv)
