import asyncio
import logging
import janus

from actionlib import ActionServer, ActionClient, CommState, GoalStatus, SimpleActionClient, SimpleActionServer
from actionlib_msgs.msg import GoalStatusArray
from functools import partial

from .topic import AsyncSubscriber

logger = logging.getLogger(__name__)


class AsyncSimpleActionClient:

    def __init__(self, ns, action_spec):
        self._client = SimpleActionClient(ns, action_spec)
        self._client.wait_for_server()

    async def send_goal(self, goal):
        self._client.send_goal(goal)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.wait_for_result)
        return self._client.get_state(), self._client.get_result()


class AsyncSimpleActionServer(SimpleActionServer):

    def __init__(self, ns, action_spec, execute, loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._execute = execute
        super().__init__(ns, action_spec, False)
        self.register_goal_callback(self._execute_cb)

    def _execute_cb(self):
        goal = self.accept_new_goal()
        future = asyncio.run_coroutine_threadsafe(self._execute(goal), self._loop)


class AsyncGoalHandle:

    def __init__(self, name, loop=None):
        self.status = None
        self.result = None

        self._name = name
        self._transition_q = janus.Queue(loop=loop)
        self._feedback_q = janus.Queue(loop=loop)
        self._old_statuses = set()

        self._done_event = asyncio.Event()
        self._status_event = asyncio.Event()

        asyncio.create_task(self._process_transitions())

    async def feedback(self):
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
        while True:
            if status in self._old_statuses:
                return
            elif self._done_event.is_set():
                raise RuntimeError(f"Action is done, will never reach status {GoalStatus.to_string(status)}")

            await self._status_event.wait()

    async def done(self):
        return self._done_event.wait()

    def cancel(self):
        # This gets injected by AsyncActionClient after init
        raise NotImplementedError()

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
                if status == GoalStatus.ACTIVE:
                    self._old_statuses.add(GoalStatus.PENDING)

            if not comm_state == CommState.DONE:
                # Re-notify awaiters when the next status comes in
                self._status_event.clear()
            else:
                self.result = result
                self._done_event.set()


class AsyncActionClient:

    def __init__(self, name, action_spec, loop=None):
        self.name = name
        self._loop = loop if loop is not None else asyncio.get_running_loop()
        self._client = ActionClient(name, action_spec)
        self._status_sub = AsyncSubscriber(name + "/status", GoalStatusArray, loop=self._loop, queue_size=1)

    def send_goal(self, goal):
        """ Send a goal to an action server. As in rospy, if you have not made sure the server is up and listening to
        the client, the goal will be swallowed.
        """
        async_handle = AsyncGoalHandle(name=self.name, loop=self._loop)
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
            handle = self.send_goal(goal)
            try:
                await asyncio.wait_for(handle.reach_status(GoalStatus.PENDING), timeout=resend_timeout)
            except asyncio.TimeoutError:
                continue
            return handle

    async def wait_for_server(self):
        """ Reserve judgement, this replicates the behavior in actionlib.ActionClient.wait_for_server """
        async for status_message in self._status_sub.subscribe():

            server_id = status_message._connection_header["callerid"]
            if self._client.pub_goal.impl.has_connection(server_id) and \
                    self._client.pub_cancel.impl.has_connection(server_id):

                status_num_pubs = 0
                for stat in self._client.status_sub.impl.get_stats()[1]:
                    if stat[4]:
                        status_num_pubs += 1

                result_num_pubs = 0
                for stat in self._client.result_sub.impl.get_stats()[1]:
                    if stat[4]:
                        result_num_pubs += 1

                feedback_num_pubs = 0
                for stat in self._client.feedback_sub.impl.get_stats()[1]:
                    if stat[4]:
                        feedback_num_pubs += 1

                if status_num_pubs > 0 and result_num_pubs > 0 and feedback_num_pubs > 0:
                    return


class AsyncActionServer:

    def __init__(self, name, action_spec, coro, loop=None):
        self.name = name
        self._loop = loop if loop is not None else asyncio.get_running_loop()
        self._coro = coro
        self._tasks = {}

        self._server = ActionServer(
            name, action_spec, goal_cb=self._goal_cb, cancel_cb=self._cancel_cb, auto_start=False)

        self._server.start()

    def _schedule_goal(self, goal_handle, goal_id):
        task = asyncio.create_task(self._coro(goal_handle))

        self._tasks[goal_id] = task

        # These methods lead to a terminal status and should cause the goal to become untracked
        for method in ['set_canceled', 'set_aborted', 'set_rejected', 'set_succeeded']:
            # print(f"wrapping {method}")
            # wrapped = getattr(goal_handle, method)

            def wrapper(wrapped, *args, **kwargs):
                print(f"calling {wrapped.__name__}")
                del self._tasks[goal_id]
                wrapped(*args, **kwargs)

            setattr(goal_handle, method, partial(wrapper, wrapped=getattr(goal_handle, method)))

        print("done wrapping")

    def _preempt_goal(self, goal_id):
        try:
            self._tasks[goal_id].cancel()
        except KeyError:
            logger.error(f"Received cancellation for untracked goal_id {goal_id}")

    def _goal_cb(self, goal_handle):
        goal_id = goal_handle.get_goal_id().id  # this is locking, should only be called from actionlib thread
        self._loop.call_soon_threadsafe(self._schedule_goal, goal_handle, goal_id)

    def _cancel_cb(self, goal_handle):
        goal_id = goal_handle.get_goal_id().id  # this is locking, should only be called from actionlib thread
        self._loop.call_soon_threadsafe(self._preempt_goal, goal_id)
