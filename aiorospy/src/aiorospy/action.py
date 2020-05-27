import asyncio
import logging
from functools import partial

import janus
import rospy
from actionlib import ActionClient, ActionServer, CommState, GoalStatus

from .helpers import ExceptionMonitor, deflector_shield, log_during
from .topic import AsyncSubscriber

logger = logging.getLogger(__name__)


class _AsyncGoalHandle:

    def __init__(self, name, exception_monitor, loop):
        """ This class should not be user-constructed """
        self._loop = loop
        self.status = None
        self.result = None

        self._name = name
        self._exception_monitor = exception_monitor
        self._feedback_queue = janus.Queue()
        self._old_statuses = set()

        self._done_event = asyncio.Event()
        self._status_cond = asyncio.Condition()

    async def feedback(self, log_period=None):
        """ Async generator providing feedback from the goal. The generator terminates when the goal
        is done.
        """
        terminal_status = asyncio.ensure_future(self._done_event.wait())
        try:
            while True:
                try:
                    new_feedback = asyncio.ensure_future(self._feedback_queue.async_q.get())
                    done, pending = await asyncio.wait(
                        {terminal_status, new_feedback},
                        return_when=asyncio.FIRST_COMPLETED,
                        timeout=log_period)

                    if new_feedback in done:
                        yield new_feedback.result()

                    elif terminal_status in done:
                        return

                    else:
                        logger.info(f"Waiting for feedback on {self.goal_id} from {self._name}")
                finally:
                    new_feedback.cancel()
                    await deflector_shield(new_feedback)
        finally:
            terminal_status.cancel()
            await deflector_shield(terminal_status)

    async def reach_status(self, status, log_period=None):
        """ Await until the goal reaches a particular status. """
        while True:
            async with self._status_cond:
                if status in self._old_statuses:
                    return
                elif self._done_event.is_set():
                    raise RuntimeError(f"Action is done, will never reach status {GoalStatus.to_string(status)}")
                else:
                    await log_during(
                        self._status_cond.wait(),
                        f"Waiting for {self.goal_id} on {self._name} to reach {GoalStatus.to_string(status)}",
                        log_period)

    async def wait(self, log_period=None):
        """ Await until the goal terminates. """
        return await log_during(
            self._done_event.wait(),
            f"Waiting for {self.goal_id} on {self._name} to complete",
            log_period
        )

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
        try:
            future = asyncio.run_coroutine_threadsafe(self._process_transition(
                # We must use these accessors here instead of passing through goal_handle to avoid hitting deadlock
                status=goal_handle.get_goal_status(),
                comm_state=goal_handle.get_comm_state(),
                text=goal_handle.get_goal_status_text(),
                result=goal_handle.get_result()
            ), loop=self._loop)
        except RuntimeError:
            # Don't raise errors if a transition comes after the event loop is shutdown
            if not self._loop.is_closed():
                raise

    def _feedback_cb(self, goal_handle, feedback):
        self._feedback_queue.sync_q.put(feedback)

    async def _process_transition(self, status, comm_state, text, result):
        async with self._status_cond:
            self.status = status
            self.comm_state = comm_state
            self.text = text

            logger.debug(f"Event in goal {self.goal_id}: status {GoalStatus.to_string(status)} result {result}")

            if self.status not in self._old_statuses:
                self._old_statuses.add(self.status)
                # (pbovbel) hack, if you accept a goal too quickly, we never see PENDING status
                # this is probably an issue elsewhere, and a DAG of action states would be great to have.
                if self.status != GoalStatus.PENDING and GoalStatus.PENDING not in self._old_statuses:
                    self._old_statuses.add(GoalStatus.PENDING)

            if self.comm_state == CommState.DONE:
                self.result = result
                self._done_event.set()

            self._status_cond.notify_all()


class AsyncActionClient:
    """ Async wrapper around the action client API. """

    def __init__(self, name, action_spec):
        self._loop = asyncio.get_event_loop()
        self.name = name
        self.action_spec = action_spec
        self._exception_monitor = ExceptionMonitor()
        self._started_event = asyncio.Event()

    async def start(self):
        """ Start the action client. """
        self._client = ActionClient(self.name, self.action_spec)
        try:
            self._started_event.set()
            await self._exception_monitor.start()
        finally:
            # TODO(pbovbel) depends on https://github.com/ros/actionlib/pull/142
            self._started_event.clear()
            self._client.stop()
            self._client = None

    async def _started(self, log_period=None):
        await log_during(self._started_event.wait(), f"Waiting for {self.name} client to be started...", period=5.0)

    async def wait_for_server(self, log_period=None):
        """ Wait for the action server to connect to this client. """
        await self._started(log_period=log_period)
        await log_during(self._wait_for_server(), f"Waiting for {self.name} server...", period=log_period)

    async def _wait_for_server(self):
        while True:
            # Use a small timeout so that the execution can be cancelled if necessary
            connected = await self._loop.run_in_executor(None, self._client.wait_for_server, rospy.Duration(0.1))
            if connected:
                return connected

    async def send_goal(self, goal):
        """ Send a goal to an action server. As in rospy, if you have not made sure the server is up and listening to
        the client, the goal will be swallowed.
        """
        await self._started(log_period=5.0)
        async_handle = _AsyncGoalHandle(name=self.name, exception_monitor=self._exception_monitor, loop=self._loop)
        sync_handle = self._client.send_goal(
            goal,
            transition_cb=async_handle._transition_cb,
            feedback_cb=async_handle._feedback_cb,
        )
        async_handle.goal_id = sync_handle.comm_state_machine.action_goal.goal_id.id
        async_handle.cancel = sync_handle.cancel

        return async_handle

    async def ensure_goal(self, goal, resend_timeout):
        """ Send a goal to an action server. If the goal is not processed by the action server within resend_timeout,
        resend the goal.
        """
        while True:
            await self.wait_for_server(log_period=5.0)
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

    def __init__(self, name, action_spec, coro, simple=False):
        """ Initialize an action server. Incoming goals will be processed via the speficied coroutine. """
        self.name = name
        self.action_spec = action_spec
        self.simple = simple
        self.tasks = {}

        self._loop = asyncio.get_event_loop()
        self._coro = coro

        self._exception_monitor = ExceptionMonitor()

    async def start(self):
        """ Start the action server. """
        self._server = ActionServer(
            self.name, self.action_spec, auto_start=False,
            # Make sure to run callbacks on the main thread
            goal_cb=partial(self._loop.call_soon_threadsafe, self._goal_cb),
            cancel_cb=partial(self._loop.call_soon_threadsafe, self._cancel_cb),
        )
        try:
            self._server.start()
            await self._exception_monitor.start()
        finally:
            # TODO(pbovbel) depends on https://github.com/ros/actionlib/pull/142
            self._server.stop()
            self._server = None

    async def cancel(self, goal_handle):
        """ Cancel a particular goal's handler task. """
        task = self._cancel_cb(goal_handle)
        if task:
            await deflector_shield(task)

    async def cancel_all(self):
        for task in self.tasks.values():
            if not task.cancelled():
                task.cancel()
            await deflector_shield(task)

    def _goal_cb(self, goal_handle):
        """ Process incoming goals by spinning off a new asynchronous task to handle the callback.
        """
        goal_id = goal_handle.get_goal_id().id
        task = asyncio.ensure_future(self._wrapper_coro(
            goal_id=goal_id,
            goal_handle=goal_handle,
            preempt_tasks={**self.tasks} if self.simple else {},
        ))
        task.add_done_callback(partial(self._task_done_callback, goal_handle=goal_handle))
        self._exception_monitor.register_task(task)
        self.tasks[goal_id] = task

    async def _wrapper_coro(self, goal_id, goal_handle, preempt_tasks={}):
        """ Wrap the user-provided coroutine to allow the simple action mode to preempt any previously submitted goals.
        """
        if preempt_tasks:
            logger.debug(f"Before goal {goal_id}, preempting {' '.join(self.tasks.keys())}")

        for other_task in preempt_tasks.values():
            if not other_task.cancelled():
                other_task.cancel()
            try:
                await deflector_shield(other_task)
            except asyncio.CancelledError:
                goal_handle.set_canceled(f"Goal {goal_id} was preempted before starting")
                raise

        logger.debug(f"Starting callback for goal {goal_id}")
        await self._coro(goal_handle)

    def _cancel_cb(self, goal_handle):
        """ Process incoming cancellations by finding the matching task and cancelling it.
        """
        goal_id = goal_handle.get_goal_id().id
        try:
            task = self.tasks[goal_id]
            task.cancel()
            return task
        except KeyError:
            logger.debug(f"Received cancellation for untracked goal_id {goal_id}")
            return None

    PENDING_STATUS = {GoalStatus.PENDING, GoalStatus.RECALLING}
    ACTIVE_STATUS = {GoalStatus.ACTIVE, GoalStatus.PREEMPTING}
    NON_TERMINAL_STATUS = PENDING_STATUS | ACTIVE_STATUS

    def _task_done_callback(self, task, goal_handle):
        """ Process finished tasks and translate the result/exception into actionlib signals.
        """
        goal_id = goal_handle.get_goal_id().id
        status = goal_handle.get_goal_status().status
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            if status in self.NON_TERMINAL_STATUS:
                message = f"Task handler was cancelled, goal {goal_id} cancelled automatically"
                goal_handle.set_canceled(text=message)
                logger.warning(
                    f"{message}. Please call set_canceled in the action server coroutine when CancelledError is raised")
        else:
            rejected_message = f"Goal {goal_id} rejected"
            aborted_message = f"Goal {goal_id} aborted"

            if exc is not None:
                reason = f"uncaught exception in actionserver handler: {exc}"
                if status in self.PENDING_STATUS:
                    goal_handle.set_rejected(result=None, text=f"{rejected_message}, {reason}")
                elif status in self.ACTIVE_STATUS:
                    goal_handle.set_aborted(result=None, text=f"{aborted_message}, {reason}")

            else:
                reason = f"never completed server-side"
                if status in self.PENDING_STATUS:
                    goal_handle.set_rejected(result=None, text=f"{rejected_message}, {reason}")
                    logger.warning(f"{rejected_message}, {reason}")
                elif status in self.ACTIVE_STATUS:
                    goal_handle.set_aborted(result=None, text=f"{aborted_message}, {reason}")
                    logger.warning(f"{aborted_message}, {reason}")

        del self.tasks[goal_id]
