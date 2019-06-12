import asyncio
import janus
import rospy

from functools import partial


class AsyncSubscriber:
    def __init__(self, name, data_class, queue_size=None, loop=None):
        """ Create an asynchronous subscriber. """
        self.name = name
        self._data_class = data_class
        self._queue_size = queue_size
        self._loop = loop if loop is not None else asyncio.get_event_loop()

    async def subscribe(self):
        """ Generator to pull messages from a subscription. """
        queue = janus.Queue(
            maxsize=self._queue_size if self._queue_size is not None else 0,
            loop=self._loop)
        self._subscriber = rospy.Subscriber(
            self.name,
            self._data_class,
            queue_size=self._queue_size,
            callback=partial(self._callback, queue=queue))
        try:
            while not rospy.is_shutdown():
                yield await queue.async_q.get()
        finally:
            self._subscriber.unregister()

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
