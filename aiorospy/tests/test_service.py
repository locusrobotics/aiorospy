#!/usr/bin/env python3.7
import aiounittest
import asyncio
import rospy
import rostest
import sys
import unittest

from std_srvs.srv import SetBool, SetBoolRequest, SetBoolResponse

from aiorospy import AsyncService


class TestServiceProxy(aiounittest.AsyncTestCase):

    @classmethod
    def setUpClass(cls):
        rospy.init_node("test_node", anonymous=True, disable_signals=True)

    def setUp(self):
        self.client = rospy.ServiceProxy("test_service", SetBool)

    async def test_service_normal(self):
        loop = asyncio.get_running_loop()
        async def callback(req):
            return SetBoolResponse(success=req.data)

        self.server = AsyncService("test_service", SetBool, callback, loop)
        server_task = asyncio.create_task(self.server.start())

        await loop.run_in_executor(None, self.client.wait_for_service)
        response = await loop.run_in_executor(None, self.client.call, True)
        self.assertEquals(True, response.success)

        server_task.cancel()

    async def test_service_exception(self):
        loop = asyncio.get_running_loop()
        async def callback(req):
            raise RuntimeError()

        self.server = AsyncService("test_service", SetBool, callback, loop)
        server_task = asyncio.create_task(self.server.start())

        await loop.run_in_executor(None, self.client.wait_for_service)

        with self.assertRaises(rospy.ServiceException):
            response = await loop.run_in_executor(None, self.client.call, True)

        with self.assertRaises(RuntimeError):
            await server_task

if __name__ == '__main__':
    rostest.rosrun('aiorospy', 'test_service_proxy', TestServiceProxy, sys.argv)
