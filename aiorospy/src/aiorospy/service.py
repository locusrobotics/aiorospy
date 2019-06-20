
import asyncio
import logging
import sys

import rospy

from .helpers import ExceptionMonitor, await_and_log

logger = logging.getLogger(__name__)


class AsyncServiceProxy:

    def __init__(self, name, service_class, loop=None):
        self.name = name
        self.service_class = service_class
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._srv_proxy = rospy.ServiceProxy(name, service_class)

    async def wait_for_service(self):
        """ Wait for a ROS service to be available. """
        while True:
            try:
                # Use a small timeout so the execution can be cancelled if necessary
                return await self._loop.run_in_executor(None, self._srv_proxy.wait_for_service, 0.1)
            except rospy.ROSException:
                continue

    async def send(self, *args, **kwargs):
        """ Send a request to a ROS service. """
        log_period = kwargs.pop('log_period', None)
        return await await_and_log(
            self._loop.run_in_executor(None, self._srv_proxy.call, *args, **kwargs),
            f"Trying to call service {self.name}...",
            log_period
        )

    async def ensure(self, *args, **kwargs):
        """ Send a request to a ROS service, retrying if comms failure is detected. """
        log_period = kwargs.pop('log_period', None)
        while True:
            await_and_log(self.wait_for_service(), f"Waiting for service {self.name}...", log_period)
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
