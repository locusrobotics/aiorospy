#!/usr/bin/env python3
import asyncio
import sys
import unittest

import aiounittest
import rospy
import rostest
from aiorospy import AsyncServiceProxy
from std_srvs.srv import SetBool, SetBoolRequest, SetBoolResponse


class TestServiceProxy(aiounittest.AsyncTestCase):

    @classmethod
    def setUpClass(cls):
        rospy.init_node("test_node", anonymous=True, disable_signals=True)

    def setUp(self):
        self.server = rospy.Service("test_service", SetBool, self.callback)

    def callback(self, req):
        return SetBoolResponse(success=req.data)

    async def test_service_proxy(self):
        client = AsyncServiceProxy("test_service", SetBool)
        response = await client.ensure(False)
        self.assertEquals(False, response.success)
        response = await client.ensure(data=True)
        self.assertEquals(True, response.success)


if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_service_proxy', TestServiceProxy, sys.argv)
