#!/usr/bin/env python3.7
import aiostream
import asyncio
import rospy
import rostest
import sys
import unittest

from std_msgs.msg import Int16

from aiorospy import AsyncSubscriber


class TestSubscriber(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rospy.init_node("test_subscriber", anonymous=True, disable_signals=True)

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

    def tearDown(self):
        self.loop.close()

    def test_subscriber(self):
        message_quantity = 5

        sub = AsyncSubscriber("test_subscriber", Int16, loop=self.loop)

        to_send = [Int16(idx) for idx in range(message_quantity)]

        async def do_pub():
            pub = rospy.Publisher(sub.name, Int16, queue_size=1)
            while pub.get_num_connections() <= 0:
                await asyncio.sleep(0.1)

            for msg in to_send:
                pub.publish(msg)

        received = []

        async def run_test():
            async for msg in sub.subscribe():
                received.append(msg)
                if len(received) == len(to_send):
                    break

        self.loop.run_until_complete(
            asyncio.wait_for(
                asyncio.gather(do_pub(), run_test(), loop=self.loop), timeout=1
            )
        )
        self.assertEqual(to_send, received)

    def test_subscriber_small_queue(self):
        queue_size = 5

        sub = AsyncSubscriber("test_subscriber_small_queue", Int16, queue_size=queue_size, loop=self.loop)
        to_send = [Int16(idx) for idx in range(10)]

        async def do_pub():
            pub = rospy.Publisher(sub.name, Int16, queue_size=queue_size)
            while pub.get_num_connections() <= 0:
                await asyncio.sleep(1)

            for msg in to_send:
                pub.publish(msg)

        received = []

        async def run_test():
            async for msg in sub.subscribe():
                received.append(msg)

        tasks = asyncio.gather(do_pub(), run_test(), loop=self.loop)

        with self.assertRaises(asyncio.TimeoutError):
            self.loop.run_until_complete(asyncio.wait_for(tasks, timeout=1))

        with self.assertRaises((asyncio.CancelledError, asyncio.TimeoutError)):
            tasks.result()

        self.assertEqual(len(received), queue_size)


if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_subscriber', TestSubscriber, sys.argv)
