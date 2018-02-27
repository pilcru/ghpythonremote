*********
Changelog
*********

1.1.3 (2018-02-27)
------------------

Fix
^^^
- Rename ``async`` import from rpyc to ``async_``.
- Bump rpyc version to pilcru/rpyc@3.4.6 to fix IronPython 2.7.0 dump bytes issues.

1.1.2 (2018-02-23)
------------------

Fix
^^^
- Use https file location for the dependencies, to remove the need for git when installing.

1.1.0 (2018-02-14)
------------------

New
^^^
- Documented ``obtain`` and ``deliver`` features of rpyc to speedup remote array-like objects creation and retrieval.

Changes
^^^^^^^
- Use the v4.0.0 pre-release of rpyc to fix IronPython <-> CPython ``str`` unpickling issues.
- Improve error messages when connection is lost.

Fix
^^^
- Repair the GH to python example, where argument passing (for the port configuration) was broken.

1.0.4 (2017-10-06)
------------------

Fix
^^^
- Fix quote escaping issue in pip install command for IronPython.

1.0.3 (2017-10-02)
------------------

First public release.