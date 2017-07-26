=============
metsaregister
=============


.. image:: https://img.shields.io/travis/valgur/metsaregister.svg
        :target: https://travis-ci.org/valgur/metsaregister

.. image:: https://codecov.io/gh/valgur/metsaregister/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/valgur/metsaregister



An unofficial Python API and command line utility to retrieve information from the `Estonian Forest Registry <http://register.metsad.ee/avalik/>`_. Provides functionality to fetch the geometries for any vector layer and to scrape the main information for forest stand or forest notification features as a GeoDataFrame or a GeoJSON file.

If you don't need detailed information about each forest stand then the `ShapeFile layers for the forest stands within each county <http://www.keskkonnaagentuur.ee/et/kaardikihid>`_, which are updated once per month, are a better alternative.

Installation
------------

Python 3.4+ is required.

.. code-block:: console

    pip install git+https://github.com/valgur/metsaregister.git

Usage
-----

A command-line tool named ``metsaregister`` is provided for convenience to query information and save it in a GeoJSON format.

Use ``--help`` to get more information about the available commands.

.. code-block:: console

    $ metsaregister --help
    Usage: metsaregister [OPTIONS] COMMAND [ARGS]...

    Options:
      --help  Show this message and exit.

    Commands:
      forest_notifications  Fetch and save forest notifications'...
      forest_stands         Fetch and save forest stands' information for...
      get_layer             Get any layer's features intersecting with a...
      list                  List available layers and their IDs

Available layers
----------------

.. code-block:: console

    $ metsaregister list
    10      Teatis
    14      Eraldised Eramets: täiskirjeldus
    11      Eraldised Eramets: osaline kirjeldus
    12      Eraldised RMK
    13      Katastrid
    213     Kaitseala
    212     Vääriselupaik
    22      Hoiualad
    23      Hooldatav sihtkaitsevöönd
    24      Natura linnualad
    25      Natura loodusala
    261     Vooluvee kalda piiranguvöönd
    262     Järve kalda piiranguvöönd
    27      Looduslik sihtkaitsevöönd
    28      Piiranguvöönd
    29      !Püsielupaigad
    210     Reservaat
    216     Jahipiirkonnad
    217     Natura toetused
    215     !1. kat loomad
    401     Võimalike uuendusraiete kaart
    311     Kogu sortiment
    312     Küttepuit
    313     Muu puit
    314     Paberipuit
    315     Palk

License
-------

MIT
