
import asyncio
import time

import rospy


class AsyncServiceProxy:

    def __init__(self, name, service_class, loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._srv_proxy = rospy.ServiceProxy(name, service_class)

    async def send(self, message):
        return await self._loop.run_in_executor(None, self._srv_proxy, message)


class AsyncService:

    def __init__(self, name, service_class, service_function, loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._service_function = service_function

        self._srv = rospy.Service(name, service_class, self._handler)

    def _handler(self, msg):
        future = asyncio.run_coroutine_threadsafe(self._service_function(msg), loop=self._loop)

        # Blocks until the future has a result.
        return future.result()
