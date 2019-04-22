import janus
import rospy


class AsyncSubscriber:

    def __init__(self, name, data_class):
        self._queue = janus.Queue()
        self._subscriber = rospy.Subscriber(name, data_class, lambda msg: self._queue.sync_q.put(msg))

        self.unregister = self._subscriber.unregister

    async def get(self):
        return await self._queue.async_q.get()


class AsyncPublisher:
    pass
