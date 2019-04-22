
import asyncio

import rospy


class AsyncServiceProxy:

    def __init__(self, name, service_class, loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._srv_proxy = rospy.ServiceProxy(name, service_class)

    async def send(self, message):
        return await self._loop.run_in_executor(None, self._srv_proxy, message)
