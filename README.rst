ghpythonremote
==============

Connect an external python instance to Grasshopper, and vice-versa.

Installation
~~~~~~~~~~~~

| Requires a Python 2.7 installation, not compatible with Python 3.
| Requires `rpyc`_, `plumbum`_.

#. To use from Rhino/IronPython to external python:

-  Install rpyc in external python with ``pip install rpyc`` from the
   command line. This will install the plumbum dependency.
-  Install ghpythonremote in Rhino/IronPython by copying the source code
   to
   ``%APPDATA%\McNeel\Rhinoceros\5.0\Plug-ins\IronPython (814d908a-e25c-493d-97e9-ee3861957f49)\settings\lib\ghpythonremote``,
   install in Rhino/IronPython by

#. To use from external python to Rhino/IronPython:

-  Install rpyc in Rhino/IronPython by extracting the ``rpyc``
   sub-directory from the `source code`_ to
   ``%APPDATA%\McNeel\Rhinoceros\5.0\Plug-ins\IronPython (814d908a-e25c-493d-97e9-ee3861957f49)\settings\lib``.
-  Install plumbum from its `source code`__ the same way: extract the
   ``plumbum`` sub-directory (found in
   ``plumbum-1.x.y.tar.gz\dist\plumbum-1.x.y.tar\plumbum-1.x.y\``) to
   ``%APPDATA%\McNeel\Rhinoceros\5.0\Plug-ins\IronPython (814d908a-e25c-493d-97e9-ee3861957f49)\settings\lib``.
-  Install ghpythonremote in external python: put ghpythonremote folder
   in the same folder as the python file being executed, or in the
   ``Lib`` folder of your python installation (by default
   ``C:\Python27\Lib``).

Usage
~~~~~

See examples in ``examples`` folder.

License
~~~~~~~

Licensed under the MIT license.

.. _rpyc: https://rpyc.readthedocs.io/en/latest/
.. _plumbum: 
.. _source code: https://pypi.python.org/packages/c5/b0/5425118bf8f209ebc863425acb37f49f71c7577dffbfaeaf0d80722e57c5/rpyc-3.3.0.zip#md5=f60bb91b46851be45363cd72e078e6ba
__ https://pypi.python.org/packages/50/15/f26f60e1bb82aabed7ff86f3fd2976784047f9a291c63ac9019086a69559/plumbum-1.6.3.tar.gz#md5=e0c588ba9271711fae3beb8c0511e8a9