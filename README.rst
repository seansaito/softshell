softshell
=========

Turn hard-coded variables into dynamic ones without refactoring.

This module allows you to run a script where you replace hard-coded
variable assignments with a list of values. For example, suppose we have
some script (``add.py``) that looks like this:

.. code:: python

    PARAM=2

    def add(x, y=2):
        return x + y
        
    print("Adding {} to 2".format(PARAM))
    print(add(PARAM))

Without changing anything in ``add.py``, you just create some
configuration (``config.yml``) file like the following:

.. code:: yaml


    ---
    path: add.py
    configurations:
        - line_number: 1
          variable: PARAM
          value: [1, 2, 3]

And then run this:

::

    $ softshell -f config.yml python add.py

    [{'configurations': [{'line_number': 1,
                          'value': [1, 2, 3],
                          'variable': 'PARAM'}],
      'path': 'add.py'}]
    Going through edit 1/3
    Configuration is: [('add.py', [(1, 'PARAM', 1)])]
    Logs can be found here: /var/folders/km/41mjphdd6553jdjjf32y9jkh0000gn/T/tmp7sr_umua
    Going through edit 2/3
    Configuration is: [('add.py', [(1, 'PARAM', 2)])]
    Logs can be found here: /var/folders/km/41mjphdd6553jdjjf32y9jkh0000gn/T/tmpn5y4b48c
    Going through edit 3/3
    Configuration is: [('add.py', [(1, 'PARAM', 3)])]
    Logs can be found here: /var/folders/km/41mjphdd6553jdjjf32y9jkh0000gn/T/tmpo4vlz7e3

You will see three separate log files, each showing the result where we
set ``PARAM`` to 1, 2, 3, respectively:

::

    $ cat /var/folders/km/41mjphdd6553jdjjf32y9jkh0000gn/T/tmp7sr_umua
    Configuration is: [('add.py', [(1, 'PARAM', 1)])]
    Adding 1 to 2
    3
    $ cat /var/folders/km/41mjphdd6553jdjjf32y9jkh0000gn/T/tmpn5y4b48c
    Configuration is: [('add.py', [(1, 'PARAM', 2)])]
    Adding 2 to 2
    4
    $ cat /var/folders/km/41mjphdd6553jdjjf32y9jkh0000gn/T/tmpo4vlz7e3
    Configuration is: [('add.py', [(1, 'PARAM', 3)])]
    Adding 3 to 2
    5

More examples can be found in the `examples <examples/>`__ directory

Installation
------------

::

    $ pip install softshell

