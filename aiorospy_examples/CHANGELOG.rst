^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package aiorospy_examples
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

0.3.0 (2022-02-23)
------------------
* Prepare for noetic release with python3 (#39)
  * replace python_interpreter 3.6 with 3
  * Check python version with setuptools
  * Fix lint
  Co-authored-by: betaboon <betaboon@0x80.ninja>
  Co-authored-by: Paul Bovbel <paul@bovbel.com>
* Contributors: Doug Smith

0.4.0 (2023-02-22)
------------------
* 0.3.0
* Update changelogs
* Prepare for noetic release with python3 (#39)
  * replace python_interpreter 3.6 with 3
  * Check python version with setuptools
  * Fix lint
  Co-authored-by: betaboon <betaboon@0x80.ninja>
  Co-authored-by: Paul Bovbel <paul@bovbel.com>
* Contributors: Doug Smith, Gary Servin

0.2.0 (2020-10-02)
------------------
* Lock requirements
* python3.6 support (`#29 <https://github.com/locusrobotics/aiorospy/issues/29>`_)
* Implement simple action server (`#26 <https://github.com/locusrobotics/aiorospy/issues/26>`_)
  Implement proper simple action server, and fix a bunch of flaky tests.
* Remove locus_msgs
* Contributors: Paul Bovbel, betaboon

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
