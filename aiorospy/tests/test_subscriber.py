#!/usr/bin/env python3
import asyncio
import sys
import unittest

import aiounittest
import rospy
import rostest
from aiorospy import AsyncSubscriber
from aiorospy.helpers import deflector_shield
from std_msgs.msg import Int16


class TestSubscriber(aiounittest.AsyncTestCase):

    @classmethod
    def setUpClass(cls):
        rospy.init_node("test_subscriber", anonymous=True, disable_signals=True)

    async def test_subscriber(self):
        message_quantity = 5
        to_send = [Int16(idx) for idx in range(message_quantity)]

        async def publish():
            pub = rospy.Publisher("test_subscriber", Int16, queue_size=message_quantity)
            while pub.get_num_connections() <= 0:
                await asyncio.sleep(0.1)

            for msg in to_send:
                pub.publish(msg)

        pub_task = asyncio.ensure_future(publish())

        received = []

        sub = AsyncSubscriber("test_subscriber", Int16)

        async for msg in sub.subscribe():
            received.append(msg)
            if len(received) == len(to_send):
                break

        self.assertEqual(to_send, received)

        pub_task.cancel()
        await deflector_shield(pub_task)

    @unittest.skip("Test is flaky, hard to be deterministic across three buffers.")
    async def test_subscriber_small_queue(self):
        queue_size = 1
        message_quantity = 10

        to_send = [Int16(idx) for idx in range(message_quantity)]

        async def publish():
            pub = rospy.Publisher("test_subscriber_small_queue", Int16, queue_size=len(to_send))
            while pub.get_num_connections() <= 0:
                await asyncio.sleep(1)

            for msg in to_send:
                pub.publish(msg)

        pub_task = asyncio.ensure_future(publish())

        received = []

        async def subscribe():
            sub = AsyncSubscriber("test_subscriber_small_queue", Int16, queue_size=queue_size)
            async for msg in sub.subscribe():
                received.append(msg)

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(subscribe(), timeout=1.0)

        self.assertTrue(len(received) < message_quantity)

        pub_task.cancel()
        await deflector_shield(pub_task)


if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_subscriber', TestSubscriber, sys.argv)
