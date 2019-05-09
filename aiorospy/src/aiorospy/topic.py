import asyncio
import janus
import rospy


class AsyncSubscriber:

    def __init__(self, name, data_class, queue_size=None, loop=None):
        self._loop = loop if loop is not None else asyncio.get_running_loop()
        self._queue = janus.Queue(maxsize=queue_size, loop=loop)
        self._subscriber = rospy.Subscriber(name, data_class, queue_size=queue_size, callback=self._callback)
        self.unregister = self._subscriber.unregister

    def _callback(self, msg):
        while True:
            try:
                self._queue.sync_q.put_nowait(msg)
                break
            except janus.SyncQueueFull:
                # Drop a message from the queue
                try:
                    _ = self._queue.sync_q.get()
                except janus.SyncQueueEmpty:
                    pass

    async def get(self):
        return await self._queue.async_q.get()


class AsyncPublisher:
    pass
