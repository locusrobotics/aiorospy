import asyncio
import concurrent.futures
import logging

import janus
import rospy

logger = logging.getLogger(__name__)


def cancel_on_shutdown(task, loop=None):
    loop = loop if loop is not None else asyncio.get_event_loop()
    rospy.on_shutdown(lambda: loop.call_soon_threadsafe(task.cancel))


def cancel_on_exception(task, loop=None):
    def handler(loop, context):
        loop.default_exception_handler(context)
        if not task.cancelled():
            task.cancel()

    loop = loop if loop is not None else asyncio.get_event_loop()
    loop.set_exception_handler(handler)


class ExceptionMonitor:
    """ Monitor exceptions in background tasks so they don't get ignored.
    """

    def __init__(self, loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._pending_tasks = set()
        self._exception_q = janus.Queue(loop=self._loop)

    async def start(self):
        """ Monitor registered background tasks, and raise their exceptions.
        """
        try:
            while True:
                exc = await self._exception_q.async_q.get()
                raise exc

        except asyncio.CancelledError as e_cancelled:
            # Cancel any tasks that will no longer be monitored
            while self._pending_tasks:
                task = self._pending_tasks.pop()
                if not task.cancelled():
                    task.cancel()

                # We can't await a concurrent.future task, make sure it comes from asyncio
                if asyncio.isfuture(task):
                    await task
            raise

        finally:
            try:
                exc = self._exception_q.async_q.get_nowait()
                raise exc
            except asyncio.QueueEmpty:
                pass

    def register_task(self, task):
        """ Register a task with the exception monitor. If the exception monitor is shutdown, all registered
        tasks will be cancelled. Supports asyncio and concurrent.futures tasks.
        """
        task.add_done_callback(self._task_done_callback)
        self._pending_tasks.add(task)

    def _task_done_callback(self, task):
        try:
            self._pending_tasks.remove(task)
        except KeyError:
            pass

        try:
            exc = task.exception()
        except (concurrent.futures.CancelledError, asyncio.CancelledError):
            pass
        else:
            if exc is not None:
                self._exception_q.sync_q.put(exc)


async def await_and_log(awaitable, msg, period):
    if period:
        try:
            return await asyncio.wait_for(awaitable, timeout=period)
        except asyncio.TimeoutError:
            logger.info(msg)
    else:
        return await awaitable
