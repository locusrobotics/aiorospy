^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package aiorospy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Forthcoming
-----------
* ServiceProxy is not threadsafe (`#36 <https://github.com/locusrobotics/aiorospy/issues/36>`_)
  (cherry picked from commit 07ea3f96dfeddce03dc0efbd75f1748c0e6eef4d)
* Contributors: Paul Bovbel

0.2.1 (2020-10-02)
------------------
* Limit the size of the action feedback queue by default (`#35 <https://github.com/locusrobotics/aiorospy/issues/35>`_)
  (cherry picked from commit 4f03362c3fef5190720f30bd37932f0ba812cb0a)
* Contributors: Alex Bencz

0.2.0 (2020-10-02)
------------------
* Missing return (`#33 <https://github.com/locusrobotics/aiorospy/issues/33>`_)
* Don't instantiate queue outside of coroutine (`#32 <https://github.com/locusrobotics/aiorospy/issues/32>`_)
* Don't take or passthrough loop arguments unnecessarily (`#31 <https://github.com/locusrobotics/aiorospy/issues/31>`_)
* Lock requirements
* python3.6 support (`#29 <https://github.com/locusrobotics/aiorospy/issues/29>`_)
* Make subprocess a context manager to ensure shutdown; expose timing vars from timer (`#28 <https://github.com/locusrobotics/aiorospy/issues/28>`_)
* Add Timer and subprocess helpers (`#27 <https://github.com/locusrobotics/aiorospy/issues/27>`_)
  * Add Timer and subprocess helpers
  * Fix comments
* Implement simple action server (`#26 <https://github.com/locusrobotics/aiorospy/issues/26>`_)
  Implement proper simple action server, and fix a bunch of flaky tests.
* run_in_executor doesn't take kwargs (`#25 <https://github.com/locusrobotics/aiorospy/issues/25>`_)
* Update to aiostream 0.3.3 (`#21 <https://github.com/locusrobotics/aiorospy/issues/21>`_)
  fixes a bug during installation in some environments, see https://github.com/vxgmichel/aiostream/pull/42
* Fix exception monitor handling of concurrent.futures.CancelledError (`#20 <https://github.com/locusrobotics/aiorospy/issues/20>`_)
* Contributors: Andreas Bresser, Paul Bovbel, betaboon

0.1.0 (2019-07-12)
------------------
* Cleanup (`#18 <https://github.com/locusrobotics/aiorospy/issues/18>`_)
  * Also stop action client to prevent memory leaks
  * Fix virtualenv for examples; drop requirement on std_srv fork
* Usability fixes (`#17 <https://github.com/locusrobotics/aiorospy/issues/17>`_)
  log_during async helper to log periodically while waiting for an awaitable
  Periodic logging to async-blocking methods in services and actions
  Automatically clean up actions that are improperly terminated
* Implement simple_actions demo; fix bug in ExecutionMonitor (`#16 <https://github.com/locusrobotics/aiorospy/issues/16>`_)
* Update internal components and examples (`#14 <https://github.com/locusrobotics/aiorospy/issues/14>`_)
  * Re-implement actions, services
  * Add tests
  * Update examples
* Allow ensure_goal to be cancelled properly (`#13 <https://github.com/locusrobotics/aiorospy/issues/13>`_)
* Fix missing await (`#12 <https://github.com/locusrobotics/aiorospy/issues/12>`_)
* get event loop not running loop (`#11 <https://github.com/locusrobotics/aiorospy/issues/11>`_)
* Sprinkle some extra docs
* Async Actions (`#7 <https://github.com/locusrobotics/aiorospy/issues/7>`_)
  Actions and subscriber rewrite
* return state and result (`#6 <https://github.com/locusrobotics/aiorospy/issues/6>`_)
  * return state and result
* Split off aiorospy_examples (`#5 <https://github.com/locusrobotics/aiorospy/issues/5>`_)
  * Split off an aiorospy_examples package to avoid pinning python version
  * Restore LICENSE and README
  * Move dependencies; use venv's default python
* Contributors: Andrew Blakey, Kaitlin Gallagher, Paul Bovbel
