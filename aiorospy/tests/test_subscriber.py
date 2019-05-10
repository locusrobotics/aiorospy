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

    def test_goal_no_queue(self):
        sub = AsyncSubscriber("test_goal_succeeded", Int16, loop=self.loop)
        magic_number = 5

        to_send = [Int16(idx) for idx in range(5)]

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
                asyncio.gather(do_pub(), run_test(), loop=self.loop), 5
            )
        )
        self.assertEqual(to_send, received)


if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_subscriber', TestSubscriber, sys.argv)
