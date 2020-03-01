import asyncio
import concurrent.futures
import functools
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

        except asyncio.CancelledError:
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
        """ When a task monitored by this ExceptionMonitor finishes, we want to check if there are any uncaught
        exceptions. Cancellations are normal and should be supressed, but everything else should be passed up to
        the monitor queue. """
        try:
            self._pending_tasks.remove(task)
        except KeyError:
            pass

        try:
            exc = task.exception()
        except asyncio.CancelledError:
            # asyncio.Future.exception will raise CancelledError
            pass
        else:
            # concurrent.futures.Future.exception will return CancelledError
            if exc is None or isinstance(exc, concurrent.futures.CancelledError):
                pass
            else:
                self._exception_q.sync_q.put(exc)


def iscoroutinefunction_or_partial(fxn):
    """ Before python3.8, asyncio.iscoroutine is unable to examine coroutines wrapped via partial.
    See https://stackoverflow.com/a/52422903/1198131
    """
    while isinstance(fxn, functools.partial):
        fxn = fxn.func
    return asyncio.iscoroutinefunction(fxn)


async def do_while(awaitable, period, do, *args, **kwargs):
    """ Convience function to periodically 'do' a callable while an awaitable is in progress. """
    if period is not None:
        task = asyncio.create_task(awaitable)
        while True:
            try:
                result = await asyncio.wait_for(
                    asyncio.shield(task),
                    timeout=period)
                return result
            except asyncio.TimeoutError:
                if iscoroutinefunction_or_partial(do):
                    await do(*args, **kwargs)
                else:
                    do(*args, **kwargs)
            except asyncio.CancelledError:
                task.cancel()
                await task
                raise
    else:
        return await awaitable


async def log_during(awaitable, msg, period, sink=logger.info):
    """ Convenience function to repeatedly log an line, while some task has not completed. """
    return await do_while(awaitable, period, sink, msg)


class ChildCancelled(asyncio.CancelledError):
    pass


async def detect_cancel(task):
    """ asyncio makes it very hard to distinguish an inner cancel from an outer cancel.
    See this thread https://stackoverflow.com/a/55424838/1198131.
    """
    cont = asyncio.get_event_loop().create_future()

    def on_done(_):
        if task.cancelled():
            cont.set_exception(ChildCancelled())
        elif task.exception() is not None:
            cont.set_exception(task.exception())
        else:
            cont.set_result(task.result())

    task.add_done_callback(on_done)
    await cont


async def deflector_shield(task):
    """ Wrap a task with deflector_shield if you want to await its completion from a coroutine, but not get cancelled
    yourself if the wrapped task is cancelled.
    """
    try:
        return await detect_cancel(asyncio.shield(task))
    except ChildCancelled:
        return None  # supress propagating an 'inner' cancel
