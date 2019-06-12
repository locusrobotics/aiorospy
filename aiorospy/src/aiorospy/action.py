import asyncio
import logging
from functools import partial

from actionlib import ActionClient, ActionServer, CommState, GoalStatus, SimpleActionClient, SimpleActionServer
from actionlib_msgs.msg import GoalStatusArray

import janus

from .topic import AsyncSubscriber
from .helpers import ExceptionMonitor

logger = logging.getLogger(__name__)


# TODO(pbovbel) remove simple clients
class AsyncSimpleActionClient:

    def __init__(self, ns, action_spec):
        self._client = SimpleActionClient(ns, action_spec)
        self._client.wait_for_server()

    async def send_goal(self, goal):
        self._client.send_goal(goal)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.wait_for_result)
        return self._client.get_state(), self._client.get_result()


# TODO(pbovbel) remove simple clients
class AsyncSimpleActionServer(SimpleActionServer):

    def __init__(self, ns, action_spec, execute, loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._execute = execute
        super().__init__(ns, action_spec, False)
        self.register_goal_callback(self._execute_cb)

    def _execute_cb(self):
        goal = self.accept_new_goal()
        future = asyncio.run_coroutine_threadsafe(self._execute(goal), self._loop)


class _AsyncGoalHandle:

    def __init__(self, name, loop=None):
        self.status = None
        self.result = None

        self._name = name
        self._transition_q = janus.Queue(loop=loop)
        self._feedback_q = janus.Queue(loop=loop)
        self._old_statuses = set()

        self._done_event = asyncio.Event(loop=loop)
        self._status_event = asyncio.Event(loop=loop)

    async def start(self):
        await self._process_transitions()

    async def feedback(self):
        """ Async generator providing feedback from the goal. The generator terminates when the goal
        is done.
        """
        while True:
            terminal_status = asyncio.create_task(self._done_event.wait())
            new_feedback = asyncio.create_task(self._feedback_q.async_q.get())
            done, pending = await asyncio.wait(
                {terminal_status, new_feedback},
                return_when=asyncio.FIRST_COMPLETED)
            if new_feedback in done:
                yield new_feedback.result()
            elif terminal_status in done:
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

            await self._status_event.wait()

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
        self._transition_q.sync_q.put((
            goal_handle.get_goal_status(),
            goal_handle.get_comm_state(),
            goal_handle.get_result()
        ))

    def _feedback_cb(self, goal_handle, feedback):
        self._feedback_q.sync_q.put(feedback)

    async def _process_transitions(self):
        while not self._done_event.is_set():
            status, comm_state, result = await self._transition_q.async_q.get()
            logger.debug(f"Action event on {self._name}: status {GoalStatus.to_string(status)} result {result}")
            self._status_event.set()

            self.status = status
            if status not in self._old_statuses:
                self._old_statuses.add(status)
                # (pbovbel) hack, if you accept a goal too quickly, we never see PENDING status
                # this is probably an issue elsewhere, and a DAG of action states would be great to have.
                if status == GoalStatus.ACTIVE:
                    self._old_statuses.add(GoalStatus.PENDING)

            if not comm_state == CommState.DONE:
                # Re-notify awaiters when the next status comes in
                self._status_event.clear()
            else:
                self.result = result
                self._done_event.set()


class AsyncActionClient:
    """ Async wrapper around the action client API. """

    def __init__(self, name, action_spec, loop=None):
        self.name = name
        self.action_spec = action_spec
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._client = ActionClient(self.name, self.action_spec)
        self._status_sub = AsyncSubscriber(self.name + "/status", GoalStatusArray, loop=self._loop, queue_size=1)
        self._exception_monitor = ExceptionMonitor(loop=loop)

    async def start(self):
        await self._exception_monitor.start()

    def send_goal(self, goal):
        """ Send a goal to an action server. As in rospy, if you have not made sure the server is up and listening to
        the client, the goal will be swallowed.
        """
        async_handle = _AsyncGoalHandle(name=self.name, loop=self._loop)
        sync_handle = self._client.send_goal(
            goal,
            transition_cb=async_handle._transition_cb,
            feedback_cb=async_handle._feedback_cb,
        )
        async_handle.cancel = sync_handle.cancel
        task = asyncio.create_task(async_handle.start())
        self._exception_monitor.register_task(task)

        return async_handle

    async def ensure_goal(self, goal, resend_timeout):
        """ Send a goal to an action server. If the goal is not processed by the action server within resend_timeout,
        resend the goal.
        """
        while True:
            await self.wait_for_server()
            handle = self.send_goal(goal)
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

    async def wait_for_server(self):
        return await self._loop.run_in_executor(None, self._client.wait_for_server)


class AsyncActionServer:
    """ Async wrapper around the action server API. """

    def __init__(self, name, action_spec, coro, loop=None, ):
        """ Initialize an action server. Incoming goals will be processed via the speficied coroutine. """
        self.name = name
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._coro = coro
        self._tasks = {}

        self._exception_monitor = ExceptionMonitor()
        self._goal_q = janus.Queue(loop=loop)
        self._cancel_q = janus.Queue(loop=loop)

        self._server = ActionServer(
            name, action_spec, goal_cb=self._goal_cb, cancel_cb=self._cancel_cb, auto_start=False)

    async def start(self):
        # TODO(pbovbel) actionservers don't stop and cause the program to not terminate
        self._server.start()
        await asyncio.gather(
            self._process_goals(),
            self._process_cancels(),
            self._exception_monitor.start()
        )

    async def _process_goals(self):
        while True:
            goal_handle, goal_id = await self._goal_q.async_q.get()

            task = asyncio.create_task(self._coro(goal_handle))
            task.add_done_callback(partial(self._task_done_callback, goal_id=goal_id))
            self._exception_monitor.register_task(task)

            self._tasks[goal_id] = task

    async def _process_cancels(self):
        while True:
            goal_id = await self._cancel_q.async_q.get()
            try:
                self._tasks[goal_id].cancel()
            except KeyError:
                logger.error(f"Received cancellation for untracked goal_id {goal_id}")


    def _task_done_callback(self, task, goal_id):
        try:
            del self._tasks[goal_id]
        except KeyError:
            pass

    def _goal_cb(self, goal_handle):
        goal_id = goal_handle.get_goal_id().id  # this is locking, should only be called from actionlib thread
        self._goal_q.sync_q.put((goal_handle, goal_id))

    def _cancel_cb(self, goal_handle):
        goal_id = goal_handle.get_goal_id().id  # this is locking, should only be called from actionlib thread
        self._cancel_q.sync_q.put(goal_id)
