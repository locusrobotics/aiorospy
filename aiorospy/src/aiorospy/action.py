import asyncio
import logging
from functools import partial

import janus
import rospy
from actionlib import ActionClient, ActionServer, CommState, GoalStatus

from .helpers import ExceptionMonitor
from .topic import AsyncSubscriber

logger = logging.getLogger(__name__)


class _AsyncGoalHandle:

    def __init__(self, name, exception_monitor, loop=None):
        """ This class should not be user-constructed """
        self.status = None
        self.result = None

        self._name = name
        self._loop = loop
        self._exception_monitor = exception_monitor
        self._feedback_queue = janus.Queue(loop=loop)
        self._old_statuses = set()

        self._done_event = asyncio.Event(loop=self._loop)
        self._status_cond = asyncio.Condition(loop=self._loop)

    async def feedback(self):
        """ Async generator providing feedback from the goal. The generator terminates when the goal
        is done.
        """
        while True:
            terminal_status = asyncio.create_task(self._done_event.wait())
            new_feedback = asyncio.create_task(self._feedback_queue.async_q.get())
            done, pending = await asyncio.wait(
                {terminal_status, new_feedback},
                return_when=asyncio.FIRST_COMPLETED)

            if new_feedback in done:
                terminal_status.cancel()
                await terminal_status
                yield new_feedback.result()

            elif terminal_status in done:
                new_feedback.cancel()
                try:
                    await new_feedback
                except asyncio.CancelledError:
                    pass
                return

            else:
                raise RuntimeError("Unexpected termination condition")

    async def reach_status(self, status):
        """ Await until the goal reaches a particular status. """
        while True:
            if status in self._old_statuses:
                return
            elif self._done_event.is_set():
                raise RuntimeError(f"Action is done, will never reach status {GoalStatus.to_string(status)}")
            else:
                async with self._status_cond:
                    await self._status_cond.wait()

    async def wait(self):
        """ Await until the goal terminates. """
        return await self._done_event.wait()

    def done(self):
        """ Specifies if the goal is terminated. """
        return self._done_event.is_set()

    def cancel(self):
        """ Cancel the goal. """
        # This gets injected by AsyncActionClient after init
        raise NotImplementedError()

    def cancelled(self):
        """ Specifies if the goal has been cancelled. """
        return self.status in {GoalStatus.PREEMPTED, GoalStatus.PREEMPTING, GoalStatus.RECALLED, GoalStatus.RECALLING}

    def _transition_cb(self, goal_handle):
        future = asyncio.run_coroutine_threadsafe(self._process_transition(
            goal_handle.get_goal_status(),
            goal_handle.get_comm_state(),
            goal_handle.get_result(),
            goal_handle.get_goal_status_text(),
        ), loop=self._loop)
        self._exception_monitor.register_task(future)

    def _feedback_cb(self, goal_handle, feedback):
        self._feedback_queue.sync_q.put(feedback)

    async def _process_transition(self, status, comm_state, result, text):
        logger.debug(f"Action event on {self._name}: status {GoalStatus.to_string(status)} result {result}")

        async with self._status_cond:
            self.status = status
            self.text = text
            if status not in self._old_statuses:
                self._old_statuses.add(status)
                # (pbovbel) hack, if you accept a goal too quickly, we never see PENDING status
                # this is probably an issue elsewhere, and a DAG of action states would be great to have.
                if status == GoalStatus.ACTIVE:
                    self._old_statuses.add(GoalStatus.PENDING)

            if comm_state == CommState.DONE:
                self.result = result
                self._done_event.set()

            self._status_cond.notify_all()


class AsyncActionClient:
    """ Async wrapper around the action client API. """

    def __init__(self, name, action_spec, loop=None):
        self.name = name
        self.action_spec = action_spec
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._exception_monitor = ExceptionMonitor(loop=self._loop)
        self._started = asyncio.Event()

    async def start(self):
        """ Start the action client. """
        self._client = ActionClient(self.name, self.action_spec)
        self._started.set()
        await self._exception_monitor.start()

    async def wait_for_server(self):
        """ Wait for the action server to connect to this client. """
        await self._started.wait()
        while True:
            # Use a small timeout so that the execution can be cancelled if necessary
            connected = await self._loop.run_in_executor(None, self._client.wait_for_server, rospy.Duration(0.1))
            if connected:
                return connected

    async def send_goal(self, goal):
        """ Send a goal to an action server. As in rospy, if you have not made sure the server is up and listening to
        the client, the goal will be swallowed.
        """
        await self._started.wait()
        async_handle = _AsyncGoalHandle(name=self.name, exception_monitor=self._exception_monitor, loop=self._loop)
        sync_handle = self._client.send_goal(
            goal,
            transition_cb=async_handle._transition_cb,
            feedback_cb=async_handle._feedback_cb,
        )
        async_handle.cancel = sync_handle.cancel

        return async_handle

    async def ensure_goal(self, goal, resend_timeout):
        """ Send a goal to an action server. If the goal is not processed by the action server within resend_timeout,
        resend the goal.
        """
        while True:
            await self.wait_for_server()
            handle = await self.send_goal(goal)
            try:
                await asyncio.wait_for(handle.reach_status(GoalStatus.PENDING), timeout=resend_timeout)
            except asyncio.TimeoutError:
                logger.warn(f"Action goal for {self.name} was not processed within timeout, resending")
                handle.cancel()
                continue
            except asyncio.CancelledError:
                handle.cancel()
                raise
            return handle


class AsyncActionServer:
    """ Async wrapper around the action server API. """

    def __init__(self, name, action_spec, coro, loop=None):
        """ Initialize an action server. Incoming goals will be processed via the speficied coroutine. """
        self.name = name
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._coro = coro
        self._tasks = {}

        self._exception_monitor = ExceptionMonitor(loop=self._loop)

        self._server = ActionServer(
            name, action_spec, goal_cb=self._goal_cb, cancel_cb=self._cancel_cb, auto_start=False)

    async def start(self):
        """ Start the action server. """
        self._server.start()
        try:
            await self._exception_monitor.start()
        finally:
            try:
                # TODO(pbovbel) depends on https://github.com/ros/actionlib/pull/142
                self._server.stop()
            except AttributeError:
                pass

    def _process_goal(self, goal_handle, goal_id):
        task = asyncio.create_task(self._coro(goal_handle))
        task.add_done_callback(partial(self._task_done_callback, goal_id=goal_id, goal_handle=goal_handle))
        self._exception_monitor.register_task(task)

        self._tasks[goal_id] = task

    def _process_cancel(self, goal_id):
        try:
            self._tasks[goal_id].cancel()
        except KeyError:
            logger.error(f"Received cancellation for untracked goal_id {goal_id}")

    def _task_done_callback(self, task, goal_id, goal_handle):
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            pass
        else:
            if exc is not None:
                status = goal_handle.get_goal_status().status
                if status in {GoalStatus.PENDING, GoalStatus.RECALLING}:
                    goal_handle.set_rejected(
                        result=None, text=f"Task rejected due to uncaught exception: {exc}")
                elif status in {GoalStatus.ACTIVE, GoalStatus.PREEMPTING}:
                    goal_handle.set_aborted(
                        result=None, text=f"Task aborted due to uncaught exception: {exc}")

        try:
            del self._tasks[goal_id]
        except KeyError:
            pass

    def _goal_cb(self, goal_handle):
        goal_id = goal_handle.get_goal_id().id  # this is locking, should only be called from actionlib thread
        self._loop.call_soon_threadsafe(self._process_goal, goal_handle, goal_id)

    def _cancel_cb(self, goal_handle):
        goal_id = goal_handle.get_goal_id().id  # this is locking, should only be called from actionlib thread
        self._loop.call_soon_threadsafe(self._process_cancel, goal_id)
