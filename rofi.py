#
#
# The MIT License
#
# Copyright (c) 2016, 2017 Blair Bonnett <blair.bonnett@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import atexit
from datetime import datetime
from decimal import Decimal, InvalidOperation
import signal
import subprocess
import time


# Python < 3.2 doesn't provide a context manager interface for Popen.
# Let's make our own wrapper if needed.
if hasattr(subprocess.Popen, '__exit__'):
    Popen = subprocess.Popen
else:
    class ContextManagedPopen(subprocess.Popen):
        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            if self.stdout:
                self.stdout.close()
            if self.stderr:
                self.stderr.close()
            if self.stdin:
                self.stdin.close()
            self.wait()
    Popen = ContextManagedPopen


class Rofi(object):
    """Class to facilitate making simple GUIs with Rofi.

    Rofi is a popup window system with minimal dependencies (xlib and pango).
    It was designed as a window switcher. Its basic operation is to display a
    list of options and let the user pick one.

    This class provides a set of methods to make simple GUIs with Rofi. It does
    this by using the subprocess module to call Rofi externally. Many of the
    methods are blocking.

    Some strings can contain Pango markup for additional formatting (those that
    can are noted as such in the docstrings). Any text in these strings *must*
    be escaped before calling Rofi. The class method Rofi.escape() performs
    this escaping for you. Make sure you call this on the text prior to adding
    Pango markup, otherwise the markup will be escaped and displayed to the
    user. See https://developer.gnome.org/pango/stable/PangoMarkupFormat.html
    for available markup.

    """
    def __init__(self, lines=None, fixed_lines=None, width=None,
                 fullscreen=None, location=None,
                 exit_hotkeys=('Alt+F4', 'Control+q'), rofi_args=None):
        """
        Parameters
        ----------
        exit_hotkeys: tuple of strings
            Hotkeys to use to exit the application. These will be automatically
            set and handled in any method which takes hotkey arguments. If one
            of these hotkeys is pressed, a SystemExit will be raised to perform
            the exit.

        The following parameters set default values for various layout options,
        and can be overwritten in any display method. A value of None means
        use the system default, which may be set by a configuration file or
        fall back to the compile-time default. See the Rofi documentation for
        full details on what the values mean.

        lines: positive integer
            The maximum number of lines to show before scrolling.
        fixed_lines: positive integer
            Keep a fixed number of lines visible.
        width: real
            If positive but not more than 100, this is the percentage of the
            screen's width the window takes up. If greater than 100, it is the
            width in pixels. If negative, it estimates the width required for
            the corresponding number of characters, i.e., -30 would set the
            width so ~30 characters per row would show.
        fullscreen: boolean
            If True, use the full height and width of the screen.
        location: integer
            The position of the window on the screen.
        rofi_args: list
            A list of other arguments to pass in to every call to rofi. These get appended
            after any other arguments

        """
        # The Popen class returned for any non-blocking windows.
        self._process = None

        # Save parameters.
        self.lines = lines
        self.fixed_lines = fixed_lines
        self.width = width
        self.fullscreen = fullscreen
        self.location = location
        self.exit_hotkeys = exit_hotkeys
        self.rofi_args = rofi_args or []

        # Don't want a window left on the screen if we exit unexpectedly
        # (e.g., an unhandled exception).
        atexit.register(self.close)


    @classmethod
    def escape(self, string):
        """Escape a string for Pango markup.

        Parameters
        ----------
        string:
            A piece of text to escape.

        Returns
        -------
        The text, safe for use in with Pango markup.

        """
        # Escape ampersands first, then other entities. Since argument is a
        # dictionary, we can't guarantee order of translations and so doing it
        # in one go would risk the ampersands in other translations being
        # escaped again.
        return string.translate(
            {38: '&amp;'}
        ).translate({
            34: '&quot;',
            39: '&apos;',
            60: '&lt;',
            62: '&gt;'
        })



    def close(self):
        """Close any open window.

        Note that this only works with non-blocking methods.

        """
        if self._process:
            # Be nice first.
            self._process.send_signal(signal.SIGINT)

            # If it doesn't close itself promptly, be brutal.
            # Python 3.2+ added the timeout option to wait() and the
            # corresponding TimeoutExpired exception. If they exist, use them.
            if hasattr(subprocess, 'TimeoutExpired'):
                try:
                    self._process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self._process.send_signal(signal.SIGKILL)

            # Otherwise, roll our own polling loop.
            else:
                # Give it 1s, checking every 10ms.
                count = 0
                while count < 100:
                    if self._process.poll() is not None:
                        break
                    time.sleep(0.01)

                # Still hasn't quit.
                if self._process.poll() is None:
                    self._process.send_signal(signal.SIGKILL)

            # Clean up.
            self._process = None


    def _run_blocking(self, args, input=None):
        """Internal API: run a blocking command with subprocess.

        This closes any open non-blocking dialog before running the command.

        Parameters
        ----------
        args: Popen constructor arguments
            Command to run.
        input: string
            Value to feed to the stdin of the process.

        Returns
        -------
        (returncode, stdout)
            The exit code (integer) and stdout value (string) from the process.

        """
        # Close any existing dialog.
        if self._process:
            self.close()

        # Make sure we grab stdout as text (not bytes).
        kwargs = {}
        kwargs['stdout'] = subprocess.PIPE
        kwargs['universal_newlines'] = True

        # Use the run() method if available (Python 3.5+).
        if hasattr(subprocess, 'run'):
            result = subprocess.run(args, input=input, **kwargs)
            return result.returncode, result.stdout

        # Have to do our own. If we need to feed stdin, we must open a pipe.
        if input is not None:
            kwargs['stdin'] = subprocess.PIPE

        # Start the process.
        with Popen(args, **kwargs) as proc:
            # Talk to it (no timeout). This will wait until termination.
            stdout, stderr = proc.communicate(input)

            # Find out the return code.
            returncode = proc.poll()

            # Done.
            return returncode, stdout


    def _run_nonblocking(self, args, input=None):
        """Internal API: run a non-blocking command with subprocess.

        This closes any open non-blocking dialog before running the command.

        Parameters
        ----------
        args: Popen constructor arguments
            Command to run.
        input: string
            Value to feed to the stdin of the process.

        """
        # Close any existing dialog.
        if self._process:
            self.close()

        # Start the new one.
        self._process = subprocess.Popen(args, stdout=subprocess.PIPE)


    def _common_args(self, allow_fullscreen=True, **kwargs):
        args = []

        # Number of lines.
        lines = kwargs.get('lines', self.lines)
        if lines:
            args.extend(['-lines', str(lines)])
        fixed_lines = kwargs.get('fixed_lines', self.fixed_lines)
        if fixed_lines:
            args.extend(['-fixed-num-lines', str(fixed_lines)])

        # Width.
        width = kwargs.get('width', self.width)
        if width is not None:
            args.extend(['-width', str(width)])

        # Fullscreen mode?
        fullscreen = kwargs.get('fullscreen', self.fullscreen)
        if allow_fullscreen and fullscreen:
            args.append('-fullscreen')

        # Location on screen.
        location = kwargs.get('location', self.location)
        if location is not None:
            args.extend(['-location', str(location)])

        # Any other arguments
        args.extend(self.rofi_args)

        # Done.
        return args


    def error(self, message, rofi_args=None, **kwargs):
        """Show an error window.

        This method blocks until the user presses a key.

        Fullscreen mode is not supported for error windows, and if specified
        will be ignored.

        Parameters
        ----------
        message: string
            Error message to show.

        """
        rofi_args = rofi_args or []
        # Generate arguments list.
        args = ['rofi', '-e', message]
        args.extend(self._common_args(allow_fullscreen=False, **kwargs))
        args.extend(rofi_args)

        # Close any existing window and show the error.
        self._run_blocking(args)


    def status(self, message, rofi_args=None, **kwargs):
        """Show a status message.

        This method is non-blocking, and intended to give a status update to
        the user while something is happening in the background.

        To close the window, either call the close() method or use any of the
        display methods to replace it with a different window.

        Fullscreen mode is not supported for status messages and if specified
        will be ignored.

        Parameters
        ----------
        message: string
            Progress message to show.

        """
        rofi_args = rofi_args or []
        # Generate arguments list.
        args = ['rofi', '-e', message]
        args.extend(self._common_args(allow_fullscreen=False, **kwargs))
        args.extend(rofi_args)

        # Update the status.
        self._run_nonblocking(args)


    def select(self, prompt, options, rofi_args=None, message="", select=None, **kwargs):
        """Show a list of options and return user selection.

        This method blocks until the user makes their choice.

        Parameters
        ----------
        prompt: string
            The prompt telling the user what they are selecting.
        options: list of strings
            The options they can choose from. Any newline characters are
            replaced with spaces.
        message: string, optional
            Message to show between the prompt and the options. This can
            contain Pango markup, and any text content should be escaped.
        select: integer, optional
            Set which option is initially selected.
        keyN: tuple (string, string); optional
            Custom key bindings where N is one or greater. The first entry in
            the tuple should be a string defining the key, e.g., "Alt+x" or
            "Delete".  Note that letter keys should be lowercase ie.e., Alt+a
            not Alt+A.

            The second entry should be a short string stating the action the
            key will take. This is displayed to the user at the top of the
            dialog. If None or an empty string, it is not displayed (but the
            binding is still set).

            By default, key1 through key9 are set to ("Alt+1", None) through
            ("Alt+9", None) respectively.

        Returns
        -------
        tuple (index, key)
            The index of the option the user selected, or -1 if they cancelled
            the dialog.
            Key indicates which key was pressed, with 0 being 'OK' (generally
            Enter), -1 being 'Cancel' (generally escape), and N being custom
            key N.

        """
        rofi_args = rofi_args or []
        # Replace newlines and turn the options into a single string.
        optionstr = '\n'.join(option.replace('\n', ' ') for option in options)

        # Set up arguments.
        args = ['rofi', '-dmenu', '-p', prompt, '-format', 'i']
        if select is not None:
            args.extend(['-selected-row', str(select)])

        # Key bindings to display.
        display_bindings = []

        # Configure the key bindings.
        user_keys = set()
        for k, v in kwargs.items():
            # See if the keyword name matches the needed format.
            if not k.startswith('key'):
                continue
            try:
                keynum = int(k[3:])
            except ValueError:
                continue

            # Add it to the set.
            key, action = v
            user_keys.add(keynum)
            args.extend(['-kb-custom-{0:s}'.format(k[3:]), key])
            if action:
                display_bindings.append("<b>{0:s}</b>: {1:s}".format(key, action))

        # And the global exit bindings.
        exit_keys = set()
        next_key = 10
        for key in self.exit_hotkeys:
            while next_key in user_keys:
                next_key += 1
            exit_keys.add(next_key)
            args.extend(['-kb-custom-{0:d}'.format(next_key), key])
            next_key += 1

        # Add any displayed key bindings to the message.
        message = message or ""
        if display_bindings:
            message += "\n" + "  ".join(display_bindings)
        message = message.strip()

        # If we have a message, add it to the arguments.
        if message:
            args.extend(['-mesg', message])

        # Add in common arguments.
        args.extend(self._common_args(**kwargs))
        args.extend(rofi_args)

        # Run the dialog.
        returncode, stdout = self._run_blocking(args, input=optionstr)

        # Figure out which option was selected.
        stdout = stdout.strip()
        index = int(stdout) if stdout else -1

        # And map the return code to a key.
        if returncode == 0:
            key = 0
        elif returncode == 1:
            key = -1
        elif returncode > 9:
            key = returncode - 9
            if key in exit_keys:
                raise SystemExit()
        else:
            self.exit_with_error("Unexpected rofi returncode {0:d}.".format(results.returncode))

        # And return.
        return index, key


    def generic_entry(self, prompt, validator=None, message=None, rofi_args=None, stdin_str="", **kwargs):
        """A generic entry box.

        Parameters
        ----------
        prompt: string
            Text prompt for the entry.
        validator: function, optional
            A function to validate and convert the value entered by the user.
            It should take one parameter, the string that the user entered, and
            return a tuple (value, error). The value should be the users entry
            converted to the appropriate Python type, or None if the entry was
            invalid. The error message should be a string telling the user what
            was wrong, or None if the entry was valid. The prompt will be
            re-displayed to the user (along with the error message) until they
            enter a valid value. If no validator is given, the text that the
            user entered is returned as-is.
        message: string
            Optional message to display under the entry.
        stdin_str: string
            Optional string to pass to rofi stdin.

        Returns
        -------
        The value returned by the validator, or None if the dialog was
        cancelled.

        Examples
        --------
        Enforce a minimum entry length:
        >>> r = Rofi()
        >>> validator = lambda s: (s, None) if len(s) > 6 else (None, "Too short")
        >>> r.generic_entry('Enter a 7-character or longer string: ', validator)

        """
        error = ""
        rofi_args = rofi_args or []

        # Keep going until we get something valid.
        while True:
            args = ['rofi', '-dmenu', '-p', prompt, '-format', 's']

            # Add any error to the given message.
            msg = message or ""
            if error:
                msg = '<span color="#FF0000" font_weight="bold">{0:s}</span>\n{1:s}'.format(error, msg)
                msg = msg.rstrip('\n')

            # If there is actually a message to show.
            if msg:
                args.extend(['-mesg', msg])

            # Add in common arguments.
            args.extend(self._common_args(**kwargs))
            args.extend(rofi_args)

            # Run it.
            returncode, stdout = self._run_blocking(args, input=stdin_str)

            # Was the dialog cancelled?
            if returncode == 1:
                return None

            # Get rid of the trailing newline and check its validity.
            text = stdout.rstrip('\n')
            if validator:
                value, error = validator(text)
                if not error:
                    return value
            else:
                return text


    def text_entry(self, prompt, message=None, allow_blank=False, strip=True,
            rofi_args=None, stdin_str="", **kwargs):
        """Prompt the user to enter a piece of text.

        Parameters
        ----------
        prompt: string
            Prompt to display to the user.
        message: string, optional
            Message to display under the entry line.
        allow_blank: Boolean
            Whether to allow blank entries.
        strip: Boolean
            Whether to strip leading and trailing whitespace from the entered
            value.
        stdin_str: String
            String to pass to rofi stdin.

        Returns
        -------
        string, or None if the dialog was cancelled.

        """
        def text_validator(text):
            if strip:
                text = text.strip()
            if not allow_blank:
                if not text:
                    return None, "A value is required."

            return text, None

        return self.generic_entry(prompt, text_validator, message, rofi_args, stdin_str, **kwargs)


    def integer_entry(self, prompt, message=None, min=None, max=None, rofi_args=None, stdin_str="", **kwargs):
        """Prompt the user to enter an integer.

        Parameters
        ----------
        prompt: string
            Prompt to display to the user.
        message: string, optional
            Message to display under the entry line.
        min, max: integer, optional
            Minimum and maximum values to allow. If None, no limit is imposed.

        Returns
        -------
        integer, or None if the dialog is cancelled.

        """
        # Sanity check.
        if (min is not None) and (max is not None) and not (max > min):
            raise ValueError("Maximum limit has to be more than the minimum limit.")

        def integer_validator(text):
            error = None

            # Attempt to convert to integer.
            try:
                value = int(text)
            except ValueError:
                return None, "Please enter an integer value."

            # Check its within limits.
            if (min is not None) and (value < min):
                return None, "The minimum allowable value is {0:d}.".format(min)
            if (max is not None) and (value > max):
                return None, "The maximum allowable value is {0:d}.".format(max)

            return value, None

        return self.generic_entry(prompt, integer_validator, message, rofi_args, stdin_str, **kwargs)


    def float_entry(self, prompt, message=None, min=None, max=None, rofi_args=None, stdin_str="", **kwargs):
        """Prompt the user to enter a floating point number.

        Parameters
        ----------
        prompt: string
            Prompt to display to the user.
        message: string, optional
            Message to display under the entry line.
        min, max: float, optional
            Minimum and maximum values to allow. If None, no limit is imposed.

        Returns
        -------
        float, or None if the dialog is cancelled.

        """
        # Sanity check.
        if (min is not None) and (max is not None) and not (max > min):
            raise ValueError("Maximum limit has to be more than the minimum limit.")

        def float_validator(text):
            error = None

            # Attempt to convert to float.
            try:
                value = float(text)
            except ValueError:
                return None, "Please enter a floating point value."

            # Check its within limits.
            if (min is not None) and (value < min):
                return None, "The minimum allowable value is {0}.".format(min)
            if (max is not None) and (value > max):
                return None, "The maximum allowable value is {0}.".format(max)

            return value, None

        return self.generic_entry(prompt, float_validator, message, rofi_args, stdin_str,stdin_str,  **kwargs)


    def decimal_entry(self, prompt, message=None, min=None, max=None, rofi_args=None, stdin_str="", **kwargs):
        """Prompt the user to enter a decimal number.

        Parameters
        ----------
        prompt: string
            Prompt to display to the user.
        message: string, optional
            Message to display under the entry line.
        min, max: Decimal, optional
            Minimum and maximum values to allow. If None, no limit is imposed.

        Returns
        -------
        Decimal, or None if the dialog is cancelled.

        """
        # Sanity check.
        if (min is not None) and (max is not None) and not (max > min):
            raise ValueError("Maximum limit has to be more than the minimum limit.")

        def decimal_validator(text):
            error = None

            # Attempt to convert to decimal.
            try:
                value = Decimal(text)
            except InvalidOperation:
                return None, "Please enter a decimal value."

            # Check its within limits.
            if (min is not None) and (value < min):
                return None, "The minimum allowable value is {0}.".format(min)
            if (max is not None) and (value > max):
                return None, "The maximum allowable value is {0}.".format(max)

            return value, None

        return self.generic_entry(prompt, decimal_validator, message, rofi_args, stdin_str, **kwargs)


    def date_entry(self, prompt, message=None, formats=['%x', '%d/%m/%Y'],
            show_example=False, rofi_args=None, stdin_str="", **kwargs):
        """Prompt the user to enter a date.

        Parameters
        ----------
        prompt: string
            Prompt to display to the user.
        message: string, optional
            Message to display under the entry line.
        formats: list of strings, optional
            The formats that the user can enter dates in. These should be
            format strings as accepted by the datetime.datetime.strptime()
            function from the standard library. They are tried in order, and
            the first that returns a date object without error is selected.
            Note that the '%x' in the default list is the current locale's date
            representation.
        show_example: Boolean
            If True, today's date in the first format given is appended to the
            message.

        Returns
        -------
        datetime.date, or None if the dialog is cancelled.

        """
        def date_validator(text):
            # Try them in order.
            for format in formats:
                try:
                    dt = datetime.strptime(text, format)
                except ValueError:
                    continue
                else:
                    # This one worked; good enough for us.
                    return (dt.date(), None)

            # None of the formats worked.
            return (None, 'Please enter a valid date.')

        # Add an example to the message?
        if show_example:
            message = message or ""
            message += "Today's date in the correct format: " + datetime.now().strftime(formats[0])

        return self.generic_entry(prompt, date_validator, message, rofi_args, stdin_str, **kwargs)


    def time_entry(self, prompt, message=None, formats=['%X', '%H:%M', '%I:%M', '%H.%M',
        '%I.%M'], show_example=False, rofi_args=None, stdin_str="", **kwargs):
        """Prompt the user to enter a time.

        Parameters
        ----------
        prompt: string
            Prompt to display to the user.
        message: string, optional
            Message to display under the entry line.
        formats: list of strings, optional
            The formats that the user can enter times in. These should be
            format strings as accepted by the datetime.datetime.strptime()
            function from the standard library. They are tried in order, and
            the first that returns a time object without error is selected.
            Note that the '%X' in the default list is the current locale's time
            representation.
        show_example: Boolean
            If True, the current time in the first format given is appended to
            the message.

        Returns
        -------
        datetime.time, or None if the dialog is cancelled.

        """
        def time_validator(text):
            # Try them in order.
            for format in formats:
                try:
                    dt = datetime.strptime(text, format)
                except ValueError:
                    continue
                else:
                    # This one worked; good enough for us.
                    return (dt.time(), None)

            # None of the formats worked.
            return (None, 'Please enter a valid time.')

        # Add an example to the message?
        if show_example:
            message = message or ""
            message += "Current time in the correct format: " + datetime.now().strftime(formats[0])

        return self.generic_entry(prompt, time_validator, message, rofi_args=None, stdin_str = stdin_str, **kwargs)


    def datetime_entry(self, prompt, message=None, formats=['%x %X'], show_example=False,
            rofi_args=None, stdin_str="", **kwargs):
        """Prompt the user to enter a date and time.

        Parameters
        ----------
        prompt: string
            Prompt to display to the user.
        message: string, optional
            Message to display under the entry line.
        formats: list of strings, optional
            The formats that the user can enter the date and time in. These
            should be format strings as accepted by the
            datetime.datetime.strptime() function from the standard library.
            They are tried in order, and the first that returns a datetime
            object without error is selected.  Note that the '%x %X' in the
            default list is the current locale's date and time representation.
        show_example: Boolean
            If True, the current date and time in the first format given is appended to
            the message.

        Returns
        -------
        datetime.datetime, or None if the dialog is cancelled.

        """
        def datetime_validator(text):
            # Try them in order.
            for format in formats:
                try:
                    dt = datetime.strptime(text, format)
                except ValueError:
                    continue
                else:
                    # This one worked; good enough for us.
                    return (dt, None)

            # None of the formats worked.
            return (None, 'Please enter a valid date and time.')

        # Add an example to the message?
        if show_example:
            message = message or ""
            message += "Current date and time in the correct format: " + datetime.now().strftime(formats[0])

        return self.generic_entry(prompt, datetime_validator, message, rofi_args, stdin_str, **kwargs)


    def exit_with_error(self, error, **kwargs):
        """Report an error and exit.

        This raises a SystemExit exception to ask the interpreter to quit.

        Parameters
        ----------
        error: string
            The error to report before quitting.

        """
        self.error(error, **kwargs)
        raise SystemExit(error)
