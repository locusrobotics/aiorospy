^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package aiorospy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

0.1.1 (2020-03-24)
------------------
* Make subprocess a context manager to ensure shutdown; expose timing vars from timer (`#28 <https://github.com/locusrobotics/aiorospy/issues/28>`_)
  (cherry picked from commit 9594cdeba80273fe75e34ed204d01cb5a90ebbcf)
* Add Timer and subprocess helpers (`#27 <https://github.com/locusrobotics/aiorospy/issues/27>`_)
  * Add Timer and subprocess helpers
  * Fix comments
  (cherry picked from commit c64378a2957b9b070d641bc35bacf425872f0fa3)
* Implement simple action server (`#26 <https://github.com/locusrobotics/aiorospy/issues/26>`_)
  Implement proper simple action server, and fix a bunch of flaky tests.
  (cherry picked from commit f4bbfee7b04a07c7cde889ccf41d9018e228e181)
* run_in_executor doesn't take kwargs (`#25 <https://github.com/locusrobotics/aiorospy/issues/25>`_)
  (cherry picked from commit 2ef6dab9d892ab2f2bf8d53190eedf19561a8cce)
* Update to aiostream 0.3.3 (`#21 <https://github.com/locusrobotics/aiorospy/issues/21>`_)
  fixes a bug during installation in some environments, see https://github.com/vxgmichel/aiostream/pull/42
  (cherry picked from commit 3252a533d9bab1be30299ebc047de57684e26058)
* Fix exception monitor handling of concurrent.futures.CancelledError (`#20 <https://github.com/locusrobotics/aiorospy/issues/20>`_)
  (cherry picked from commit 2380daed9038a7abb66fdbc7052c8dbd82209238)
* Contributors: Andreas Bresser, Paul Bovbel

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
