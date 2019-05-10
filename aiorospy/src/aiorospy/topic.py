import asyncio
import janus
import rospy

from functools import partial


class AsyncSubscriber:
    def __init__(self, name, data_class, queue_size=None, loop=None):
        self._name = name
        self._data_class = data_class
        self._queue_size = queue_size
        self._loop = loop if loop is not None else asyncio.get_running_loop()

    # TODO(pbovbel) should we check rospy.is_shutdown() instead of while True?
    async def subscribe(self):
        queue = janus.Queue(maxsize=self._queue_size, loop=self._loop)
        self._subscriber = rospy.Subscriber(
            self._name, self._data_class, queue_size=self._queue_size, callback=partial(self._callback, queue=queue))
        while True:
            yield await queue.async_q.get()

    def _callback(self, msg, queue):
        while True:
            try:
                queue.sync_q.put_nowait(msg)
                break
            except janus.SyncQueueFull:
                # Drop a single message from the queue
                try:
                    _ = queue.sync_q.get()
                except janus.SyncQueueEmpty:
                    pass


class AsyncPublisher(rospy.Publisher):
    pass
