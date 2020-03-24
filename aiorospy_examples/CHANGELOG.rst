^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package aiorospy_examples
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

0.1.1 (2020-03-24)
------------------
* Implement simple action server (`#26 <https://github.com/locusrobotics/aiorospy/issues/26>`_)
  Implement proper simple action server, and fix a bunch of flaky tests.
  (cherry picked from commit f4bbfee7b04a07c7cde889ccf41d9018e228e181)
* Remove locus_msgs
  (cherry picked from commit a36176707e367d40cb583682c001b7c75cd7467d)
* Contributors: Paul Bovbel

0.1.0 (2019-07-12)
------------------
* Cleanup (`#18 <https://github.com/locusrobotics/aiorospy/issues/18>`_)
  * Also stop action client to prevent memory leaks
  * Fix virtualenv for examples; drop requirement on std_srv fork
* Idiomatic bool random
* Usability fixes (`#17 <https://github.com/locusrobotics/aiorospy/issues/17>`_)
  log_during async helper to log periodically while waiting for an awaitable
  Periodic logging to async-blocking methods in services and actions
  Automatically clean up actions that are improperly terminated
* Implement simple_actions demo; fix bug in ExecutionMonitor (`#16 <https://github.com/locusrobotics/aiorospy/issues/16>`_)
* Update internal components and examples (`#14 <https://github.com/locusrobotics/aiorospy/issues/14>`_)
  * Re-implement actions, services
  * Add tests
  * Update examples
* Async Actions (`#7 <https://github.com/locusrobotics/aiorospy/issues/7>`_)
  Actions and subscriber rewrite
* return state and result (`#6 <https://github.com/locusrobotics/aiorospy/issues/6>`_)
  * return state and result
* Split off aiorospy_examples (`#5 <https://github.com/locusrobotics/aiorospy/issues/5>`_)
  * Split off an aiorospy_examples package to avoid pinning python version
  * Restore LICENSE and README
  * Move dependencies; use venv's default python
* Contributors: Kaitlin Gallagher, Paul Bovbel
