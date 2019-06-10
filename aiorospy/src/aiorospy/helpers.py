import asyncio
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
