# python-rofi

A Python module to make simple GUIs by calling Rofi.


## What is Rofi?

[Rofi](https://davedavenport.github.io/rofi/) is a popup window switcher with
minimal dependencies. Its basic operation is to display a list of options and
let the user pick one. The following screenshot is shamelessly hotlinked from
the Rofi website (which you should probably visit if you want actual details
about Rofi!) and shows it being used by the [teiler screenshot
application](https://carnager.github.io/teiler/).

![Teiler screenshot](https://davedavenport.github.io/rofi/images/rofi/dmenu-replacement.png)


## What is this module?

It simplifies making simple GUIs using Rofi. It provides a class with a number
of methods for various GUI actions (show messages, pick one of these options,
enter some text / a number). These are translated to the appropriate Rofi
command line options, and then the standard
[subprocess](https://docs.python.org/3/library/subprocess.html) module is used
to run Rofi. Any output is then processed and returned to you to do whatever
you like with.


## How stable is it?

Now that's a loaded question... this is only a few days old so there is bound
to be some tweaking to come yet. I think the API is logical so I don't think
that will change too much (never say ever though!). It works fine in the
project I wrote it for, but there are bound to be bugs and missing features at
this stage.


## Requirements

Well, you need to have the `rofi` executable available on the system path
(i.e., install Rofi!).


## What Python versions are supported?

Right now, only Python 3.5 -- the new
[subprocess.run()](https://docs.python.org/3/library/subprocess.html#subprocess.run)
function is used in several places. I do intend to make it compatible with
Python 2.7 at some point though.


## What license does it use?

The MIT license, the same as Rofi itself. The full text is in the
[LICENSE](LICENSE) file in the repository.
