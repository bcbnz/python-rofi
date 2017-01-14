===========
python-rofi
===========

A Python module to make simple GUIs using Rofi.


What is Rofi?
=============

Rofi_ is a popup window switcher with minimal dependencies. Its basic operation
is to display a list of options and let the user pick one. The following
screenshot is shamelessly hotlinked from the Rofi website (which you should
probably visit if you want actual details about Rofi!) and shows it being used
by the teiler_ screenshot application.

.. image:: https://davedavenport.github.io/rofi/images/rofi/dmenu-replacement.png
   :alt: A screenshot of the teiler application using Rofi.

.. _Rofi: https://davedavenport.github.io/rofi/

.. _teiler: https://carnager.github.io/teiler/


What is this module?
====================

It simplifies making simple GUIs using Rofi. It provides a class with a number
of methods for various GUI actions (show messages, pick one of these options,
enter some text / a number). These are translated to the appropriate Rofi
command line options, and then the standard subprocess_ module is used to run
Rofi. Any output is then processed and returned to you to do whatever you like
with.

.. _subprocess: https://docs.python.org/3/library/subprocess.html


Requirements
============

You need to have the `rofi` executable available on the system path (i.e.,
install Rofi!).


What Python versions are supported?
===================================

It *should* work with any version of Python from 2.7 onwards. It may work with
older versions, though no specific support for them will be added. It is
developed on Python 2.7 and Python 3.6 -- the latest versions of the Python 2
and 3 branches respectively.


What license does it use?
=========================

The MIT license, the same as Rofi itself.
