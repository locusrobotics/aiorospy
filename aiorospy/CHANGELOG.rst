^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package aiorospy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

0.3.0 (2022-02-23)
------------------
* Prepare for noetic release with python3 (#39)
  * replace python_interpreter 3.6 with 3
  * Check python version with setuptools
  * Fix lint
  Co-authored-by: betaboon <betaboon@0x80.ninja>
  Co-authored-by: Paul Bovbel <paul@bovbel.com>
* Wait for a service longer (#37)
  * Don't wait for service in ensure
  * Don't pre-empt wait_for_service as often
* ServiceProxy is not threadsafe (#36)
* Limit the size of the action feedback queue by default (#35)
* Contributors: Doug Smith, Paul Bovbel, abencz

0.4.0 (2023-02-22)
------------------
* 0.3.0
* Update changelogs
* Add exponential delay when retrying service after exception (#40)
* Prepare for noetic release with python3 (#39)
  * replace python_interpreter 3.6 with 3
  * Check python version with setuptools
  * Fix lint
  Co-authored-by: betaboon <betaboon@0x80.ninja>
  Co-authored-by: Paul Bovbel <paul@bovbel.com>
* Wait for a service longer (#37)
  * Don't wait for service in ensure
  * Don't pre-empt wait_for_service as often
* ServiceProxy is not threadsafe (#36)
* Limit the size of the action feedback queue by default (#35)
* Contributors: Alex Bencz, Doug Smith, Gary Servin, Paul Bovbel, abencz

0.5.0 (2023-09-25)
------------------
* 0.4.0
* Update changelogs
* 0.3.0
* Update changelogs
* Add exponential delay when retrying service after exception (#40)
* Prepare for noetic release with python3 (#39)
  * replace python_interpreter 3.6 with 3
  * Check python version with setuptools
  * Fix lint
  Co-authored-by: betaboon <betaboon@0x80.ninja>
  Co-authored-by: Paul Bovbel <paul@bovbel.com>
* Wait for a service longer (#37)
  * Don't wait for service in ensure
  * Don't pre-empt wait_for_service as often
* ServiceProxy is not threadsafe (#36)
* Limit the size of the action feedback queue by default (#35)
* Contributors: Alex Bencz, Doug Smith, Gary Servin, Paul Bovbel, abencz

0.11.1 (2025-12-22)
-------------------

0.11.0 (2025-09-30)
-------------------
* chore: apply centralized pre-commit fixes (#49)
  * Fix flake8 errors
* Contributors: Bianca Bendris

0.10.0 (2025-06-06)
-------------------
* Update packages dependencies to build on Noble (#48)
  * Update dependencies
  * Update cmake minimum version
  * Update dependecies
  * Update github actions
  * Match versions to the lowest common version
* Contributors: Gary Servin

0.9.0 (2025-02-04)
------------------

0.8.0 (2024-09-16)
------------------
* Don't use async_generator for python3.9+ (#47)
* Fix async generator dependency (#46)
  * Fix naming of async generator dependency
  * Use contextlib if available
* Contributors: Gary Servin, Michael Johnson

0.7.0 (2024-06-17)
------------------
* RST-9628 re-create service proxy after transport terminated (#45)
* Contributors: Alex Bencz

0.6.0 (2024-02-02)
------------------
* 0.5.0
* Update changelogs
* 0.4.0
* Update changelogs
* 0.3.0
* Update changelogs
* Add exponential delay when retrying service after exception (#40)
* Prepare for noetic release with python3 (#39)
  * replace python_interpreter 3.6 with 3
  * Check python version with setuptools
  * Fix lint
  Co-authored-by: betaboon <betaboon@0x80.ninja>
  Co-authored-by: Paul Bovbel <paul@bovbel.com>
* Wait for a service longer (#37)
  * Don't wait for service in ensure
  * Don't pre-empt wait_for_service as often
* ServiceProxy is not threadsafe (#36)
* Limit the size of the action feedback queue by default (#35)
* Contributors: Alex Bencz, Doug Smith, Gary Servin, Paul Bovbel, abencz

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
