#!/usr/bin/env python3
import asyncio
import unittest

import aiounittest

from aiorospy.helpers import ChildCancelled, detect_cancel, deflector_shield


class TestDetectCancel(aiounittest.AsyncTestCase):

    async def test_success(self):
        """Task completes normally - detect_cancel returns the result."""
        async def coro():
            return "result"

        task = asyncio.ensure_future(coro())
        result = await detect_cancel(task)
        self.assertEqual("result", result)

    async def test_exception(self):
        """Task raises an exception - detect_cancel re-raises it."""
        async def failing():
            raise ValueError("boom")

        task = asyncio.ensure_future(failing())
        with self.assertRaises(ValueError, msg="boom"):
            await detect_cancel(task)

    async def test_inner_cancel(self):
        """Task is cancelled internally - detect_cancel raises ChildCancelled."""
        task = asyncio.ensure_future(asyncio.sleep(100))
        await asyncio.sleep(0)
        task.cancel()

        with self.assertRaises(ChildCancelled):
            await detect_cancel(task)

    async def test_outer_cancel(self):
        """Outer awaiter is cancelled - CancelledError (not ChildCancelled) propagates."""
        task = asyncio.ensure_future(asyncio.sleep(100))
        outer_task = asyncio.ensure_future(detect_cancel(task))

        await asyncio.sleep(0)
        outer_task.cancel()

        results = await asyncio.gather(outer_task, return_exceptions=True)
        exc = results[0]
        self.assertIsInstance(exc, asyncio.CancelledError)
        self.assertNotIsInstance(exc, ChildCancelled)

        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def test_outer_cancel_race_with_task_completion(self):
        """Race condition: outer is cancelled at the same time the inner task completes.

        Previously, on_done would call set_result/set_exception on the already-cancelled
        cont future, raising InvalidStateError and crashing the event loop.
        """
        loop = asyncio.get_event_loop()

        asyncio_exceptions = []
        original_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda l, ctx: asyncio_exceptions.append(ctx.get('exception')))

        try:
            task_may_finish = asyncio.Event()

            async def slow_task():
                await task_may_finish.wait()
                return "result"

            task = asyncio.ensure_future(slow_task())
            outer_task = asyncio.ensure_future(detect_cancel(task))

            # Let outer_task run until it is suspended inside detect_cancel awaiting cont.
            await asyncio.sleep(0)

            # Cancel the outer task, which cancels cont.
            outer_task.cancel()
            await asyncio.sleep(0)

            # Now let the inner task complete - this fires on_done on the already-cancelled cont.
            task_may_finish.set()
            await asyncio.sleep(0)
            await asyncio.sleep(0)

            await task

            self.assertEqual(
                [], asyncio_exceptions,
                f"asyncio callback raised unexpected exception(s): {asyncio_exceptions}"
            )
        finally:
            loop.set_exception_handler(original_handler)

    async def test_outer_cancel_race_with_task_exception(self):
        """Race condition: outer is cancelled while the inner task simultaneously raises an exception.

        The task exception must be retrieved to prevent asyncio's
        "Task exception was never retrieved" error.
        """
        loop = asyncio.get_event_loop()

        asyncio_exceptions = []
        original_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda l, ctx: asyncio_exceptions.append(ctx.get('exception')))

        try:
            task_may_raise = asyncio.Event()

            async def failing_task():
                await task_may_raise.wait()
                raise ValueError("boom")

            task = asyncio.ensure_future(failing_task())
            outer_task = asyncio.ensure_future(detect_cancel(task))

            await asyncio.sleep(0)

            outer_task.cancel()
            await asyncio.sleep(0)

            task_may_raise.set()
            await asyncio.sleep(0)
            await asyncio.sleep(0)

            await asyncio.gather(outer_task, task, return_exceptions=True)

            self.assertEqual(
                [], asyncio_exceptions,
                f"asyncio callback raised unexpected exception(s): {asyncio_exceptions}"
            )
        finally:
            loop.set_exception_handler(original_handler)


        loop = asyncio.get_event_loop()

        asyncio_exceptions = []
        original_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda l, ctx: asyncio_exceptions.append(ctx.get('exception')))

        try:
            task = asyncio.ensure_future(asyncio.sleep(100))
            outer_task = asyncio.ensure_future(detect_cancel(task))

            await asyncio.sleep(0)

            # Cancel both simultaneously.
            outer_task.cancel()
            task.cancel()
            await asyncio.sleep(0)
            await asyncio.sleep(0)

            await asyncio.gather(outer_task, task, return_exceptions=True)

            self.assertEqual(
                [], asyncio_exceptions,
                f"asyncio callback raised unexpected exception(s): {asyncio_exceptions}"
            )
        finally:
            loop.set_exception_handler(original_handler)


class TestDeflectorShield(aiounittest.AsyncTestCase):

    async def test_success(self):
        """Task completes normally - deflector_shield returns the result."""
        async def coro():
            return "result"

        task = asyncio.ensure_future(coro())
        result = await deflector_shield(task)
        self.assertEqual("result", result)

    async def test_exception(self):
        """Task raises an exception - deflector_shield propagates it."""
        async def failing():
            raise ValueError("boom")

        task = asyncio.ensure_future(failing())
        with self.assertRaises(ValueError):
            await deflector_shield(task)

    async def test_inner_cancel_returns_none(self):
        """Inner task is cancelled - deflector_shield suppresses ChildCancelled and returns None."""
        task = asyncio.ensure_future(asyncio.sleep(100))
        await asyncio.sleep(0)
        task.cancel()

        result = await deflector_shield(task)
        self.assertIsNone(result)

    async def test_outer_cancel(self):
        """Outer awaiter is cancelled - CancelledError propagates out of deflector_shield."""
        task = asyncio.ensure_future(asyncio.sleep(100))
        outer_task = asyncio.ensure_future(deflector_shield(task))

        await asyncio.sleep(0)
        outer_task.cancel()

        results = await asyncio.gather(outer_task, return_exceptions=True)
        self.assertIsInstance(results[0], asyncio.CancelledError)

        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def test_outer_cancel_race_with_task_completion(self):
        """Race condition: outer is cancelled while the shielded task simultaneously completes.

        on_done fires on the already-cancelled cont - must not raise InvalidStateError.
        """
        loop = asyncio.get_event_loop()

        asyncio_exceptions = []
        original_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda l, ctx: asyncio_exceptions.append(ctx.get('exception')))

        try:
            task_may_finish = asyncio.Event()

            async def slow_task():
                await task_may_finish.wait()
                return "result"

            task = asyncio.ensure_future(slow_task())
            outer_task = asyncio.ensure_future(deflector_shield(task))

            await asyncio.sleep(0)

            outer_task.cancel()
            await asyncio.sleep(0)

            task_may_finish.set()
            await asyncio.sleep(0)
            await asyncio.sleep(0)

            await task

            self.assertEqual(
                [], asyncio_exceptions,
                f"asyncio callback raised unexpected exception(s): {asyncio_exceptions}"
            )
        finally:
            loop.set_exception_handler(original_handler)

    async def test_outer_cancel_race_with_task_exception(self):
        """Race condition: outer is cancelled while the shielded task simultaneously raises an exception.

        The task exception must be retrieved to prevent asyncio's
        "Task exception was never retrieved" error.
        """
        loop = asyncio.get_event_loop()

        asyncio_exceptions = []
        original_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda l, ctx: asyncio_exceptions.append(ctx.get('exception')))

        try:
            task_may_raise = asyncio.Event()

            async def failing_task():
                await task_may_raise.wait()
                raise ValueError("boom")

            task = asyncio.ensure_future(failing_task())
            outer_task = asyncio.ensure_future(deflector_shield(task))

            await asyncio.sleep(0)

            outer_task.cancel()
            await asyncio.sleep(0)

            task_may_raise.set()
            await asyncio.sleep(0)
            await asyncio.sleep(0)

            await asyncio.gather(outer_task, task, return_exceptions=True)

            self.assertEqual(
                [], asyncio_exceptions,
                f"asyncio callback raised unexpected exception(s): {asyncio_exceptions}"
            )
        finally:
            loop.set_exception_handler(original_handler)

    async def test_outer_cancel_race_with_inner_cancel(self):
        """Race condition: outer is cancelled while the inner task is simultaneously cancelled.

        The shield wrapper becomes cancelled (mirroring the inner cancel), firing on_done
        on an already-cancelled cont - must not raise InvalidStateError.
        """
        loop = asyncio.get_event_loop()

        asyncio_exceptions = []
        original_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda l, ctx: asyncio_exceptions.append(ctx.get('exception')))

        try:
            task = asyncio.ensure_future(asyncio.sleep(100))
            outer_task = asyncio.ensure_future(deflector_shield(task))

            await asyncio.sleep(0)

            outer_task.cancel()
            task.cancel()
            await asyncio.sleep(0)
            await asyncio.sleep(0)

            await asyncio.gather(outer_task, task, return_exceptions=True)

            self.assertEqual(
                [], asyncio_exceptions,
                f"asyncio callback raised unexpected exception(s): {asyncio_exceptions}"
            )
        finally:
            loop.set_exception_handler(original_handler)


if __name__ == '__main__':
    unittest.main()
