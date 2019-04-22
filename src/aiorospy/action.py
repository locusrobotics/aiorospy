import asyncio

from actionlib import SimpleActionClient, SimpleActionServer


class AsyncSimpleActionClient:

    def __init__(self, ns, action_spec):
        self._client = SimpleActionClient(ns, action_spec)
        self._client.wait_for_server()

    async def send_goal(self, goal):
        self._client.send_goal(goal)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.wait_for_result)
        return self._client.get_result()


class AsyncSimpleActionServer(SimpleActionServer):

    def __init__(self, ns, action_spec, execute, loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._execute = execute
        super().__init__(ns, action_spec, False)
        self.register_goal_callback(self._execute_cb)

    def _execute_cb(self):
        goal = self.accept_new_goal()
        asyncio.run_coroutine_threadsafe(self._execute(goal), self._loop)
