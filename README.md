# aiorospy

An asyncio wrapper around rospy I/O interfaces for Python >=3.6 to enable use of the co-operative multitasking concurrency model.


## Rationale

Rospy implements its I/O interfaces using callbacks and therefore handles concurrency with a preemptive multitasking model. This means that complex nodes need to worry about threading concerns such as locking (and therefore deadlocks), as well as how to structure callback-based control flow in a sane manner. If you've attempted to write a sufficiently complex rospy node that handles I/O from different sources, you probably understand how painful this can get.

Asyncio was added to the Python 3.5 standard library on a provisional bases, formalized in Python 3.6. It implements the capabilities to handle concurrency with a co-operative multitasking model. This means that a complex node can more easily manage its core loop through the use of `awaitables` in a single thread. This tends to make your code straightforward to write, reason about, and debug. If you're not convinced, check out the example that handles about a dozen I/O interfaces in a single event loop.

`Aiorospy` and `asyncio` might be for you if:
- your rospy node wants to handle I/O from numerous sources in a complex manner
- you're trying to implement a WebSocket or HTTP server in a single process alongside topics, services, and actions (if a multi-process WSGI/ASGI with IPC feels like overkill)
- you've grown to hate maintaining complex rospy nodes because of callback hell, locking noise, and deadlocking
- you're tired of having to debug complex rospy nodes where the core control flow jumps among countless threads
- you want precdictability over what will happen next and in what order

## Requirements

### Python >= 3.6
Asyncio does not exist in Python 2 and is only provisional in Python 3.5.  If you're using Xenial, you can install it using the [deadsnakes](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa) ppa.

### [catkin_virtualenv](https://github.com/locusrobotics/catkin_virtualenv)
Simplifies dependency management and makes using a different version of python pretty easy. Check `requirements.txt` to see what dependencies are used when this package is built.

## Examples

Check out the scripts folder.

With a roscore running:

```
rosrun aiorospy aiorospy_telephone
```

## How it works
There's no desire to reimplement rospy this late in its life, so this package wraps the various rospy interfaces instead. This means that there are still underlying threads that handle TCP I/O for topics and services. But unlike `rospy`, the API is not callbacks that run in separate threads, but rather `awaitables` that run in the main thread's event loop.  This is accomplished by using thread-safe intermediaries such as `asyncio.call_soon_threadsafe` and `janus.Queue`.

Note the use of `disable_signals=True` and `rospy.signal_shutdown()` in the examples. This is necessary to give asyncio control of shutting down the event loop and application in general. Alternatively you can manually call `loop.stop()` and do cleanup yourself.

## TODO
- Implement the non-Simple ActionClient and ActionServer
- Explore need for `queue_size` to be handled.
