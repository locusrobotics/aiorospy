
import asyncio
import logging
import rospy
import sys

from .helpers import ExceptionMonitor


logger = logging.getLogger(__name__)


class AsyncServiceProxy:

    def __init__(self, name, service_class, loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._srv_proxy = rospy.ServiceProxy(name, service_class)

    async def wait_for_service(self):
        """ Wait for a ROS service to be available. """
        return await self._loop.run_in_executor(None, self._srv_proxy.wait_for_service)

    async def send(self, *args, **kwargs):
        """ Send a request to a ROS service. """
        return await self._loop.run_in_executor(None, self._srv_proxy.call, *args, **kwargs)

    async def ensure(self, *args, **kwargs):
        """ Send a request to a ROS service, retrying if comms failure is detected. """
        while True:
            await self.wait_for_service()
            try:
                return await self.send(*args, **kwargs)
            except (rospy.ServiceException, AttributeError, rospy.exceptions.ROSException,
                    rospy.exceptions.ROSInternalException) as e:
                logger.exception(f"Caught exception {e}, retrying service call")
                continue

class AsyncService:

    def __init__(self, name, service_class, coro, loop=None):
        self.name = name
        self.service_class = service_class
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._coro = coro
        self._exception_monitor = ExceptionMonitor(loop=self._loop)

    async def start(self):
        """ Start the ROS service server """
        self._srv = rospy.Service(
            self.name, self.service_class, self._handler,
            # We don't need rospy's internal exception handler, which just logs the errors.
            error_handler=lambda e, exc_type, exc_value, tb: None
        )

        try:
            await self._exception_monitor.start()
        finally:
            self._srv.shutdown()

    def _handler(self, msg):
        future = asyncio.run_coroutine_threadsafe(self._coro(msg), loop=self._loop)

        self._exception_monitor.register_task(future)

        # Blocks until the future has a result.
        return future.result()
