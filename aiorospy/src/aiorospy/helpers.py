import asyncio
import concurrent.futures
import janus
import logging

logger = logging.getLogger(__name__)


def stop_on_exception_handler(loop, context):
    loop.default_exception_handler(context)
    if loop.is_running():
        loop.stop()


async def stop_loop_on_exception(awaitable):
    try:
        return await awaitable
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception(f"Uncaught exception in awaitable: {e}")
        asyncio.get_running_loop().stop()


# TODO(pbovbel) create stop on exception decorator?


def cancel_all_tasks(loop):
    to_cancel = asyncio.all_tasks(loop)
    if not to_cancel:
        return

    for task in to_cancel:
        task.cancel()

    loop.run_until_complete(
        asyncio.gather(*to_cancel, return_exceptions=True))

    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler({
                'message': 'unhandled exception during loop shutdown',
                'exception': task.exception(),
                'task': task,
            })


def cancel_on_exception_handler(loop, context, task):
    loop.default_exception_handler(context)
    if not task.cancelled():
        task.cancel()


class ExceptionMonitor:
    """ Monitor exceptions in background tasks so they don't get swallowed.
    """

    def __init__(self, loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._exception_q = janus.Queue(loop=self._loop)

    async def start(self):
        try:
            while True:
                exc = await self._exception_q.async_q.get()
                raise exc
        except asyncio.CancelledError as e_cancelled:
            try:
                exc = self._exception_q.async_q.get_nowait()
                raise exc
            except asyncio.QueueEmpty:
                raise e_cancelled

    def register_task(self, task):
        task.add_done_callback(self._task_done_callback)

    def register_tasks(self, tasks):
        for task in tasks:
            self.register_task(task)

    def _task_done_callback(self, task):
        try:
            exc = task.exception()
        except (concurrent.futures.CancelledError, asyncio.CancelledError):
            pass
        else:
            if exc is not None:
                self._exception_q.sync_q.put(exc)
