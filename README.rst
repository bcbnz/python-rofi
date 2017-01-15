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


Examples
--------

Data entry
~~~~~~~~~~

The simplest example is to create a Rofi instance and prompt the user to enter
a piece of text::

    from rofi import Rofi
    r = Rofi()
    name = r.text_entry('What is your name? ')

There are also entry methods for integers, floating-point numbers, and decimal
numbers::

    age = r.integer_entry('How old are you? ')
    height = r.float_entry('How tall are you? ')
    price = r.decimal_entry('How much are you willing to spend? ')

All of these return the corresponding Python type. Dates and times can also be
requested::

    dob = r.date_entry('What is your date of birth? ')
    start = r.time_entry('When do you start work? ')
    reminder = r.datetime_entry('When do you want to be alerted? ')

Again, these return the corresponding Python type. By default, they expect the
user to enter something in the appropriate format for the current locale. You
can override this by providing a list of format specifiers to any of these
functions. The available specifiers are detailed in the Python documentation
for the datetime_ module. For example::

    start = r.time_entry('When do you start work? ', formats=['%H:%M'])

All of these entry methods are specialisations of the ``generic_entry()``
method. You can use this to create your own entry types. All you need to do is
create a validator function which takes the text entered by the user, and
returns either the Python object or an error message. For example, to enforce a
minimum length on an entered piece of text::

    validator = lambda s: (s, None) if len(s) > 6 else (None, "Too short!")
    r.generic_entry('Enter a 7-character or longer string: ', validator)

Note that all of these methods return ``None`` if the dialog is cancelled.

.. _datetime: https://docs.python.org/3/library/datetime.html

Errors
~~~~~~

To show an error message to the user::

    r.error('I cannot let you do that.')
    r.exit_with_error('I cannot let you do that.')

The latter shows the error message and then exits.

Selections
~~~~~~~~~~

To give the user a list of things to select from, and return the index of the
option they chose::

    options = ['Red', 'Green', 'Blue', 'White', 'Silver', 'Black', 'Other']
    index, key = r.select('What colour car do you drive?', options)

The returned ``key`` value tells you what key the user pressed. For Enter, the
value is 0, while -1 indicates they cancelled the dialog. You can also specify
custom key bindings::

    index, key = r.select('What colour car do you drive?', options, key5=('Alt+n', "I don't drive"))

In this case, the returned ``key`` will be 5 if they press Alt+n.

Status
~~~~~~

To display a status message to the user::

    r.status("I'm working on that...")

This is the only non-blocking method (all the others wait for the user to
finish before returning control to your script). To close the status message::

    r.close()

Calling a display or entry method will also close any status message currently
displayed.

Messages
~~~~~~~~

Any of the entry methods and the select method have an optional argument
``message``. This is a string which is displayed below the prompt. The string
can contain Pango_ markup::

    r.text_entry('What are your goals for this year? ', message='Be <b>bold</b>!')

If you need to escape a string to avoid it being mistaken for markup, use the
``Rofi.escape()`` class method::

    msg = Rofi.escape('Format: <firstname> <lastname>')
    r.text_entry('Enter your name: ', message=msg)

.. _Pango:  https://developer.gnome.org/pango/stable/PangoMarkupFormat.html

Customisation
~~~~~~~~~~~~~

There are a number of options available to customise the display. These can be
set in the initialiser to apply to every dialog displayed, or you can pass them
to any of the display methods to change just that dialog. See the Rofi
documentation for full details of these parameters.

* ``lines``: The maximum number of lines to show before scrolling.

* ``fixed_lines``: Keep a fixed number of lines visible.

* ``width``: If positive but not more than 100, this is the percentage of the
  screen's width the window takes up. If greater than 100, it is the width in
  pixels. If negative, it estimates the width required for the corresponding
  number of characters, i.e., -30 would set the width so approximately 30
  characters per row would show.

* ``fullscreen``: If True, use the full height and width of the screen.

* ``location``:  The position of the window on the screen.


Requirements
============

You need to have the ``rofi`` executable available on the system path (i.e.,
install Rofi!). Everything else that python-rofi needs is provided by the
Python standard libraries.


What Python versions are supported?
===================================

It *should* work with any version of Python from 2.7 onwards. It may work with
older versions, though no specific support for them will be added. It is
developed on Python 2.7 and Python 3.6 -- the latest versions of the Python 2
and 3 branches respectively.


What license does it use?
=========================

The MIT license, the same as Rofi itself.


Bug reports
===========

The project is developed on GitHub_. Please file any bug reports or feature
requests on the Issues_ page there.

.. _GitHub: https://github.com/bcbnz/python-rofi
.. _Issues: https://github.com/bcbnz/python-rofi/issues
