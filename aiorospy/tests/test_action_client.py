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

    def create_server(self, ns, goal_cb, auto_start=True):
        action_server = ActionServer(ns, TestAction, goal_cb=goal_cb, auto_start=False)
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

        await client.wait_for_server()
        goal_handle = client.send_goal(TestGoal(1))
        async for idx, feedback in aiostream.stream.enumerate(goal_handle.feedback()):
            self.assertEqual(feedback, TestFeedback(idx))

        self.assertEqual(GoalStatus.SUCCEEDED, goal_handle.status)
        self.assertEqual(expected_result, goal_handle.result)

    async def test_wait_for_result(self):
        received_accepted = Event()

        def goal_cb(goal_handle):
            goal_handle.set_accepted()
            received_accepted.wait()
            goal_handle.set_succeeded(result=TestResult(0))

        server = self.create_server("test_wait_for_result", goal_cb)
        client = AsyncActionClient(server.ns, TestAction)

        await client.wait_for_server()
        goal_handle = client.send_goal(TestGoal(1))
        await goal_handle.reach_status(GoalStatus.ACTIVE)

        received_accepted.set()

        with self.assertRaises(RuntimeError):
            await goal_handle.reach_status(GoalStatus.REJECTED)

        await goal_handle.reach_status(GoalStatus.SUCCEEDED)

        with self.assertRaises(RuntimeError):
            await goal_handle.reach_status(GoalStatus.REJECTED)

    async def test_ensure(self):
        def goal_cb(goal_handle):
            goal_handle.set_accepted()

        server = self.create_server("test_ensure", goal_cb, auto_start=False)
        client = AsyncActionClient(server.ns, TestAction)

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(client.ensure_goal(TestGoal(), resend_timeout=0.1), timeout=1)

        server.start()

        goal_handle = await client.ensure_goal(TestGoal(), resend_timeout=0.1)
        await goal_handle.reach_status(GoalStatus.ACTIVE)


if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_action_client', TestActionClient, sys.argv)
