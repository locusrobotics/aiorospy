import asyncio
import janus

from actionlib import ActionClient
from actionlib import CommState
from actionlib import SimpleActionClient
from actionlib import SimpleActionServer


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

    # def is_ready(self):
    #     """ cribbed from actionlib.ActionClient.wait_for_server """
    #     if self._client.last_status_msg:
    #         server_id = self._client.last_status_msg._connection_header['callerid']

    #         if self._client.pub_goal.impl.has_connection(server_id) and \
    #                 self._client.pub_cancel.impl.has_connection(server_id):
    #             # We'll also check that all of the subscribers have at least
    #             # one publisher, this isn't a perfect check, but without
    #             # publisher callbacks... it'll have to do
    #             status_num_pubs = 0
    #             for stat in self._client.status_sub.impl.get_stats()[1]:
    #                 if stat[4]:
    #                     status_num_pubs += 1

    #             result_num_pubs = 0
    #             for stat in self._client.result_sub.impl.get_stats()[1]:
    #                 if stat[4]:
    #                     result_num_pubs += 1

    #             feedback_num_pubs = 0
    #             for stat in self._client.feedback_sub.impl.get_stats()[1]:
    #                 if stat[4]:
    #                     feedback_num_pubs += 1

    #             if status_num_pubs > 0 and result_num_pubs > 0 and feedback_num_pubs > 0:
    #                 return True

    #     return False


class AsyncGoalHandle:

    def __init__(self):
        self._status_q = janus.Queue()
        self._feedback_q = janus.Queue()
        self._old_statuses = set()
        self.status = None
        self.result = None

        self._done_event = asyncio.Event()
        self._status_event = asyncio.Event()
        asyncio.create_task(self._process_status())

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

    async def wait_for_status(self, status):
        while True:
            await self._status_event.wait()
            if status in self._old_statuses:
                return
            elif self._done_event.is_set():
                raise RuntimeError(f"Action is done, will never reach status {status}")

    async def done(self):
        return self._done_event.wait()

    def cancel(self):
        # This gets injected by AsyncActionClient after init
        raise NotImplementedError()

    def _transition_cb(self, goal_handle):
        self._status_q.sync_q.put((
            goal_handle.get_goal_status(),
            goal_handle.get_comm_state(),
            goal_handle.get_result()
        ))

    def _feedback_cb(self, goal_handle, feedback):
        self._feedback_q.sync_q.put(feedback)

    async def _process_status(self):
        while not self._done_event.is_set():
            status, comm_state, result = await self._status_q.async_q.get()
            self._status_event.set()

            if status not in self._old_statuses:
                self.status = status
                self._old_statuses.add(status)

            if comm_state == CommState.DONE:
                self.result = result
                self._done_event.set()
            else:
                self._status_event.clear()

class AsyncActionClient:

    def __init__(self, name, action_spec):
        self.name = name
        self._client = ActionClient(name, action_spec)

    def send_goal(self, goal):

        # while not self.is_ready():
        #     await asyncio.sleep(0.1)
        self._client.wait_for_server() # TODO(pbovbel) replace with async wait

        async_handle = AsyncGoalHandle()
        sync_handle = self._client.send_goal(goal,
            transition_cb=async_handle._transition_cb,
            feedback_cb=async_handle._feedback_cb,
        )
        async_handle.cancel = sync_handle.cancel
        return async_handle
