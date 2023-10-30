#!/usr/bin/env python3

VERSION = 45            # Version of this package
DEBUG_PRINT = False     # Set this to True to log all print() output
DEBUG_INPUT = False     # Set this to True to log all input received
DELAY_INPUT = False     # Set this to True to take 1 second to process each key

import os
import re
import textwrap
import unicodedata

# Return a getch() wrapper, depending on the OS being called from
if os.name == "nt":
    class GetChWrapper:
        # Windows variant of getch(), use Win32 API to detect the difference
        # from Escape vs an extended key code
        def __init__(self):
            import msvcrt
        def __enter__(self):
            return self
        def __call__(self, timeout=False):
            import msvcrt
            if timeout:
                if not msvcrt.kbhit():
                    return None
            return chr(msvcrt.getch()[0])
        def __exit__(self, *args, **kargs):
            pass
else:
    import sys
    import termios
    class GetChWrapper:
        # Unix variant of getch(), handle termios logic to
        # emulate a timed getch() call so we can detect ESC
        # versus an extended key press
        def __init__(self):
            self.fd = sys.stdin.fileno()
            self.old_settings = termios.tcgetattr(self.fd)
            self.new_settings = termios.tcgetattr(self.fd)
            self.new_settings[3] &= ~(termios.ECHO | termios.ICANON)
            self.new_settings[6][termios.VMIN] = 0
            self.new_settings[6][termios.VTIME] = 0
            termios.tcsetattr(self.fd, termios.TCSANOW, self.new_settings)
        def __enter__(self):
            return self
        def __call__(self, timeout=False):
            if timeout:
                ret = os.read(self.fd, 1)
                _debug_getch(ret, "_getch_unix.1")
                if ret is None or len(ret) == 0:
                    return None
                else:
                    return chr(ret[0])
            else:
                while True:
                    ret = os.read(self.fd, 1)
                    if ret is not None and len(ret) > 0:
                        _debug_getch(ret, "_getch_unix.2")
                        return chr(ret[0])
        def __exit__(self, *args, **kargs):
            termios.tcsetattr(self.fd, termios.TCSANOW, self.old_settings)

if DEBUG_PRINT:
    # Useful helper code to log what's being output, saves all output
    # to a file "_print_output_log_"
    _old_print = print
    def print(*args, **kargs):
        import json, datetime, sys
        if sys.version_info >= (3, 11): from datetime import UTC
        else: UTC=datetime_fix.timezone.utc
        # Reverse ansi codes to the syntax used by print_ansi
        temp = re.sub("[<>]", lambda m: {"<":"<open>",">":"<close>"}[m.group(0)], args[0])
        for ansi, desc in [
            ("\x1b[?25l", "hide"), ("\x1b[?25h", "show"), ("\x1b[7m", "invert"), ("\x1b[0m", "revert"), 
            ("\x1b[s", "save(SCO)"), ("\x1b[u", "restore(SCO)"), ("\x1b7", "save"), ("\x1b8", "restore"),
            ("\x1b[6n", "report"), ("\x1b[4m", "underline"), ("\x1b[24m", "notunderline")]:
            temp = temp.replace(ansi, "<" + desc + ">")
        def arrows(m):
            ret = {"A": "up", "B": "down", "C": "right", "D": "left"}[m.group("dir")]
            ret += (" " + m.group("num")) if len(m.group("num")) > 0 else ""
            return "<" + ret + ">"
        temp = re.sub("\x1b\\[(?P<num>[0-9]+)(?P<dir>[ABCD])", arrows, temp)
        with open("_print_output_log_", "a") as f:
            # Print out whatever's passed to print
            f.write(json.dumps([datetime.datetime.now(UTC).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"), args[1:], kargs]) + "\n")
            # And show each line of output line by line to make it easier to view
            temp = temp.replace("\n", "\n\x01")
            for row in temp.split("\x01"):
                f.write(json.dumps(row) + "\n")
            f.write("\n")
        # Call the real print implementation
        _old_print(*args, **kargs)


def _ansi_code(m):
    # Helper to turn <x> codes into ANSI output
    code = m.group("code")
    num = m.group("num")
    if num is None:
        num = ""

    if _simple_mode:
        temp = {
            "open": "<",
            "close": ">",
        }.get(code, "")
    else:
        temp = {
            "open": "<",
            "close": ">",
            "hide": "\x1b[?25l",
            "show": "\x1b[?25h",
            "invert": "\x1b[7m",
            "bold": "\x1b[1m",
            "underline": "\x1b[4m",
            "notunderline": "\x1b[24m",
            "revert": "\x1b[0m",
            "save": "\x1b7",
            "restore": "\x1b8",
            "report": "\x1b[6n",
            "up": "\x1b[{num}A",
            "down": "\x1b[{num}B",
            "left": "\x1b[{num}D",
            "right": "\x1b[{num}C",
        }.get(code, None)

    if temp is None:
        raise Exception("Unknown ansi code: " + code)
    
    return temp.format(num=num)


def escape_ansi(value):
    # Escapes an string so it will print as-is in ANSI output
    ret = ""
    for x in value:
        if x == "<":
            ret += "<open>"
        elif x == ">":
            ret += "<close>"
        else:
            ret += x
    return ret


def _debug_getch(value, call_no):
    if DEBUG_INPUT:
        import json, datetime, sys
        if sys.version_info >= (3, 11): from datetime import UTC
        else: UTC=datetime_fix.timezone.utc
        if value is None:
            msg = "<none>"
        elif isinstance(value, str):
            if len(value) == 1:
                if 32 <= ord(value) <= 126:
                    msg = f"0x{ord(value):02x} {value}"
                else:
                    msg = f"0x{ord(value):02x}"
            else:
                msg = json.dumps(value)
        else:
            msg = str(value)
        with open("_getch_log_", "a") as f:
            # Print out whatever's gotten as input
            f.write(json.dumps([
                datetime.datetime.now(UTC).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"), 
                msg,
                call_no]) + "\n")
    return value


def getkey(getch):
    # Use getch to detect a single key press, and decode
    # some common keys to pretty strings
    ret = _debug_getch(getch(), "getkey.1")
    if ret == "\x03":
        # Ctrl-C, treat it as Ctrl-C
        raise KeyboardInterrupt()
    elif ret == "\x08" or ret == "\x7f":
        return "back"
    elif ret in {"\x0d", "\x0a"}:
        ret = "enter"
    elif ret == "\xe0":
        # This is the start of a win32 extended code, get the
        # next key
        ret = _debug_getch(getch(), "getkey.2")
        ret = {
            "\x47": "home",
            "\x4f": "end",
            "\x49": "pageup",
            "\x51": "pagedown",
            "\x48": "up",
            "\x50": "down",
            "\x4b": "left",
            "\x4d": "right",
        }.get(ret, ret)
    elif ret == "\x1b":
        if os.name == "nt":
            # On NT, this is always escape
            return "esc"
        else:
            # On Unix, we need to peek for the next key
            second = _debug_getch(getch(timeout=True), "getkey.3")
            if second is None:
                # We didn't get one quickly, assume the escape key was pressed
                return "esc"
            else:
                if second == "\x5b" or second == "\x4f":
                    # Ok, got the second character in a three byte sequence, get the third
                    second = _debug_getch(getch(), "getkey.4")
                    ret = {
                        "\x31": "home",
                        "\x34": "end",
                        "\x48": "home",
                        "\x46": "end",
                        "\x35": "pageup",
                        "\x36": "pagedown",
                        "\x41": "up",
                        "\x42": "down",
                        "\x44": "left",
                        "\x43": "right",
                    }.get(second, second)
                    if second in {"\x31", "\x34", "\x35", "\x36"}:
                        # These XTerm sequences end with another key
                        _debug_getch(getch(), "getkey.5")
                # else .. well, it doesn't matter what we do, so fall back to return the
                # raw code, it's as good an answer as any

    return ret


def get_ansi(value, simple_mode=None):
    # Turn a string like "This is <invert>inverted<revert>" into the 
    # escape sequences to send it to an ANSI terminal
    if simple_mode is not None:
        global _simple_mode
        old_simple_mode = _simple_mode
        _simple_mode = simple_mode

    # Also handle <code #> to pass a number along to the ANSI code
    value = re.sub("<(?P<code>[a-z]+?)(| (?P<num>[0-9]+))>", _ansi_code, value)

    if simple_mode is not None:
        _simple_mode = old_simple_mode
    
    return value


def print_ansi(value, flush=False):
    # Print out an ANSI code, decoding it first
    print(get_ansi(value), end="", flush=flush)


def len_ansi(value):
    # Helper to get the length of an ANSI string in terms of number of characters that are displayed
    return len(get_ansi(value, simple_mode=True))


_need_enable = True
_simple_mode = False
def enable_ansi():
    # Turn ANSI mode on, only necessary for NT, because it's FUN!
    global _need_enable
    global _simple_mode
    if _need_enable:
        _need_enable = False
        if os.name == "nt":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            if kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7) == 0:
                _simple_mode = True


def get_term_size(getch):
    # Get the size of the terminal, really, just move to the bottom right corner, 
    # ask the terminal "where are we", and report the results
    enable_ansi()
    print_ansi("<save><right 999><down 999><report><restore>", flush=True)
    temp = ""
    while True:
        temp += _debug_getch(getch(), "get_term_size")
        if temp[-1] == 'R':
            break
    # Ignore any extra characters that might be in the buffer
    while len(temp) > 0 and temp[:2] != "\x1b[":
        temp = temp[1:]

    if temp.startswith("\x1b[") and temp.endswith("R"):
        # If the string we got looks correct, then parse it
        temp = temp[2:-1].split(';')
        return int(temp[1]), int(temp[0])
    else:
        # Otherwise, just return a default value
        return 25, 80

def _split_items(opts, multiline, width):
    temp = []
    for cur in opts:
        cur_multiline = multiline

        # Pull out the description
        if isinstance(cur, dict):
            desc = cur["desc"]
            cur_multiline = cur.get("multiline", cur_multiline)
        elif isinstance(cur, (list, tuple)):
            desc = cur[0]
        else:
            desc = cur

        if len(desc) > width and cur_multiline > 1:
            # This line can be split, go ahead and split it
            orig_desc = desc
            desc = textwrap.wrap(desc, width=width, subsequent_indent="  ", max_lines=cur_multiline, placeholder="...")

            # And create multiple items to put it into
            for part in desc[:-1]:
                temp.append({"desc": part, "highlight_next": True})

            # Store the original description, along with the other values
            if isinstance(cur, dict):
                cur["desc"] = desc[-1]
                cur["orig_desc"] = orig_desc
                temp.append(cur)
            elif isinstance(cur, (list, tuple)):
                safe_dupe = {
                    "desc": desc[-1],
                    "orig_desc": orig_desc,
                }
                if len(cur) > 1:
                    safe_dupe["ret"] = cur[1]
                temp.append(safe_dupe)
            else:
                temp.append({
                    "desc": desc[-1],
                    "orig_desc": orig_desc,
                })
        else:
            # This line can't be split, just add it as is
            temp.append(cur)
    return temp


def unicode_len(value):
    # Helper to return the length of a string taking into account full width characters that take 
    # up two spots in a traditional output terminal
    value = re.sub("\x1b\\[[0-9]+m", "", value)
    return len(value) + sum(unicodedata.east_asian_width(x) in 'FW' for x in value)


class Settings():
    # A class to save and restore settings, and present a small TUI allowing the user
    # to toggle settings.
    def __init__(self, fn, options):
        # fn: The filename to store the settings in.  It will be created if it does
        #     not exist, or is otherwise invalid
        # options: The different options, along with available settings, for instance:
        #          (
        #              ("enabled", (
        #                  ("Enabled: On", True),
        #                  ("Enabled: Off", False),
        #              )),
        #              ("debug_level", (
        #                  ("Debug: Off", "off"),
        #                  ("Debug: Warnings", "warnings"),
        #                  ("Debug: All", "all"),
        #              ))
        #          )
        #          Would define two settings, one a bool, and one an enum with three
        #          options.  The first option in each list is the default.
        self.options = options
        self.data = {}
        self.fn = fn
        if os.path.isfile(fn):
            import json
            with open(fn, "rt") as f:
                self.data = json.load(f)
        for key, opts in self.options:
            self.data[key] = self.data.get(key, opts[0][1])
            if self.data[key] not in set(x[1] for x in opts):
                self.data[key] = opts[0][1]

    def pick_settings(self):
        # Show a list of options and let use change them
        def get_desc(key):
            for item_key, options in self.options:
                if item_key == key:
                    for desc, setting in options:
                        if self.data[key] == setting:
                            return desc
            raise Exception()
        def toggle_setting(opt):
            key = opt['ret']
            for item_key, options in self.options:
                if item_key == key:
                    for i, (desc, setting) in enumerate(options):
                        if self.data[key] == setting:
                            i = (i + 1) % len(options)
                            self.data[key] = options[i][1]
                            return options[i][0]
            raise Exception()

        opts = [{
            "desc": get_desc(key), 
            "ret": key, 
            "callback": toggle_setting, 
            "done_show": True,
        } for key, value in self.options]

        opts.append(("Save and exit", "__exit__"))

        opt = list_picker(opts, left_right=True)
        if opt == "__exit__":
            self.save()

    def save(self):
        # Save current settings to data file
        import json
        with open(self.fn, "wt") as f:
            json.dump(self.data, f, indent=4, sort_keys=True)
            f.write("\n")

    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value

def list_picker(opts, max_rows=-1, line_numbers=True, scroll_bar=True, keep_header=False, wasd=False, left_right=False, multiline=1):
    # Show a menu of options, allow the user to use arrow keys to select, enter text to filter down 
    # options and return a code based off the selection.
    #
    # opts: Should be a list of options (see below).
    # max_rows: Value showing the max number of options to show at once, by default it will limit
    #           based off of the terminal size.
    # line_numbers: Allows disabling the auto-line numbers that are added to options.
    # scroll_bar: Turn off the fake scroll bar on the side if the list overflows the 
    #             available space.
    # keep_header: Keeps a header (non return value) above the selected item.
    # wasd: Allows using "w", "a", "s", and "d" as arrow keys, though it does prevent the entry 
    #       of these keys as a filter.
    # left_right: Causes the right arrow key to act as enter and select an item, and the left 
    #             arrow to escape.
    # multiline: Menu items can span multiple lines using textwrap to line wrap the text.
    #
    # Each option is:
    #   str - A simple string to shown, can not be selected
    #   (str,) - A string to be shown, can not be selected
    #   (str, ret) - A string to be shown, along with a return value.
    #                If the return value is not None, then it can be selected
    #   {
    #       "desc": str,            = The item to show
    #       "ret": ret,             = The value to return when selected, None means the option is 
    #                                 not selectable
    #       "underline": bool,      = Underline anything in square brackets
    #       "default": bool,        = This option is selected by default
    #       "keep": bool,           = The menu is kept on screen after this option is selected
    #       "shortcut": str,        = The value to use instead of a line number for this option
    #       "hide_shortcut": bool,  = Hide the shortcut for this item
    #       "done_hide": bool,      = Hide this item when any item is selected
    #       "done_show": bool,      = Show this item when another item is selected
    #       "always_show": bool,    = Always show this item, even when the user filters items
    #       "multiline": int,       = A per-item override for the multiline value
    #       "callback": func,       = Call func when the item is selected, see Callback below
    #       "any_key": bool,        = Call 'callback' function for any non-arrow key on this item
    #   }
    # 
    # Callback:
    # 
    # If the callback returns a string, the menu item is updated, if it returns None, the option 
    # is selected if it can be.  It can also return a dict like {"<ret>": "<desc>"} to update the 
    # description for multiple items.  If the description is changed, any user selected filters
    # are removed if they no longer match, and any default menu item is selected again.
    # 
    # The callback is called with a dictionary of {"desc": "--", "ret": "--"}
    #
    # If "any_key" is enabled for this menu item, then the call back dictionary will have an 
    # additional key of "key" with the key-press value.  If it returns None, the key press 
    # is handled normally, otherwise the return value is called with the same dictionary after
    # ensuring the input and output will work normally.  The callback can be wrapped in a dictionary
    # like {"clear": False, "callback": func, "use_callback": True} to prevent the screen updates 
    # if the secondary callback will only update menu items

    with GetChWrapper() as getch:
        enable_ansi()
        term_width, term_height = get_term_size(getch)
        offset = 0
        if max_rows == -1:
            max_rows = term_height

        # Break up any options that need to be broken to multiple lines
        opts = _split_items(opts, multiline, term_width-7)

        rows = min(max_rows, len(opts))
        filter = ""
        selected = 0
        move_up = 0
        shown = {}
        temp = []

        if line_numbers:
            max_index = len([x for x in opts if isinstance(x, (tuple, list)) and len(x) > 1 and x[1] is not None])
            pad = len(str(max_index))

        class ItemDesc:
            def __init__(self, desc="", ret=None):
                self.pre = ""               # either the line number, or the "shortcut", padded for display
                self.line_number = None     # The line number, used for display and default shortcut
                self.desc = desc            # "desc", or the first item in a tuple, the item to display
                self.orig_desc = desc       # The complete "desc" for multiline displays
                self.display = desc         # What from "desc" is displayed due to screen size
                self.trimmed = None         # Used by the trim helper to ensure it's not over trimming
                self.ret = ret              # "ret", or the second item in a tuple, the return value when selected
                self.underline = False      # "underline", this item has underlines for square brackets
                self.default = False        # "default", this item is selected by default
                self.keep = False           # "keep", keep the menu on screen if this item is selected
                self.shortcut = None        # "shortcut", an override for the shortcut instead of the line number
                self.hide_shortcut = False  # "hide_shortcut", hide the shortcut displayed for this item
                self.always_show = False    # "always_show", always show this, even during filters
                self.header = None          # The header for this item, that is the previous non-return item
                self.done_hide = False      # Hide this element when any item is selected
                self.done_show = False      # Show this element when another item is selected
                self.callback = None        # Callback to call when this item is selected
                self.any_key = False        # Should the callback be called for random key presses?
                self.multiline = multiline  # An override line wrap for this specific item
                self.highlight_next = False # Internal only flag to highlight this item with the next item
                self.temp = False           # Temp bool flag used when filtering items

        default_opt = None
        line_number = 0
        last_header = None

        # Crack the user options
        for cur in opts:
            item = ItemDesc()
            temp.append(item)
            if isinstance(cur, dict):
                item.desc = cur.get("desc", "")
                item.orig_desc = cur.get("orig_desc", cur.get("desc", ""))
                item.ret = cur.get("ret", None)
                if item.ret is not None:
                    if cur.get("default", False):
                        default_opt = len(temp) - 1
                        item.default = True
                    if cur.get("keep", False):
                        item.keep = True
                # Pull out the other values, note the careful handling here
                # to do things like turn bool-like things into bool, and such
                item.shortcut = cur.get("shortcut", None)
                item.callback = cur.get("callback", None)
                item.underline = True if cur.get("underline", False) else False
                item.any_key = True if cur.get("any_key", False) else False
                item.hide_shortcut = True if cur.get("hide_shortcut", False) else False
                item.done_hide = True if cur.get("done_hide", False) else False
                item.done_show = True if cur.get("done_show", False) else False
                item.multiline = int(cur.get("multiline", multiline))
                item.highlight_next = True if cur.get("highlight_next", False) else False
                item.always_show = True if cur.get("always_show", False) else False
                if item.shortcut is not None:
                    if not isinstance(item.shortcut, str):
                        item.shortcut = None
            elif isinstance(cur, (tuple, list)):
                if len(cur) == 1:
                    item.desc, item.ret = cur[0], None
                else:
                    item.desc, item.ret = cur[0], cur[1]
                item.orig_desc = item.desc
            else:
                item.desc, item.ret = cur, None
                item.orig_desc = item.desc

            if item.ret is not None:
                line_number += 1
                item.line_number = line_number
            if keep_header:
                if item.ret is None and not item.highlight_next:
                    last_header = item
                else:
                    item.header = last_header
            item.desc = re.sub("[\r\n\t]", " ", item.desc)

        # Create the display
        quick_filter = {}
        if line_numbers:
            # We have line numbers, so take the extra space into account when limiting the line
            pad = max([unicode_len(x.shortcut) for x in temp if x.shortcut is not None], default=1)
            pad = max(pad, max(len(str(x.line_number)) for x in temp if x.line_number is not None))

            for i, item in enumerate(temp):
                shortcut = item.shortcut if item.shortcut is not None else str(item.line_number)
                if item.ret is not None:
                    quick_filter[shortcut] = i

                if item.ret is not None and not item.hide_shortcut:
                    item.pre = f" {(' ' * pad + shortcut)[-pad:]}]"
                else:
                    item.pre = " " * (pad + 2)
        else:
            # No line numbers, so a bit more space, but we still need space to handle the ">" and "<" chevrons
            # selection markers + space at start + extra space at end of line
            for item in temp:
                item.pre = " "

        opts = temp
        filtered = [x for x in opts]
        max_desc_len = 0

        def trim_descs():
            # Helper to trim the descriptions for display, this can be called again and again
            # if something changes, like the scroll bar being shown or hidden
            nonlocal max_desc_len

            # x = term_width - (<two spaces for chevrons> + <one for extra space>)
            x = term_width - (2 + 1)

            # if the scroll bar is shown, then add two extra spaces for it
            if len(filtered) > rows and scroll_bar:
                x -= 2
            for item in opts:
                if item.trimmed != item.desc:
                    item.trimmed = item.desc
                    item.display = item.desc
                    codes = []
                    if item.underline:
                        temp = ""
                        for test_char in item.display:
                            if test_char == "[":
                                codes.append((len(temp), get_ansi('<underline>')))
                            elif test_char == "]":
                                codes.append((len(temp), get_ansi('<notunderline>')))
                            else:
                                temp += test_char
                        item.display = temp
                    target = max(3, x - unicode_len(item.pre))
                    if unicode_len(item.display) > target:
                        temp = item.display
                        while unicode_len(temp) > target-3:
                            temp = temp[:-1]
                        item.display = temp + "..."
                    for pos, code in codes[::-1]:
                        item.display = item.display[:pos] + code + item.display[pos:]
            max_desc_len = max(unicode_len(x.display) for x in opts)

        trim_descs()
        picked_option = None

        # Helper to move the display focus.  This will move it up or down and
        # move the offset if necessary
        def move_selection(move_dir, wrap=False):
            nonlocal selected, offset
            if move_dir == 1:
                if selected == len(filtered) - 1:
                    if wrap:
                        selected = 0
                        offset = 0
                    return False
                else:
                    if offset + rows - 1 == selected:
                        offset += 1
                    selected += 1
                    return True
            else:
                if selected == 0:
                    if wrap:
                        selected = len(filtered) - 1
                        offset = max(0, len(filtered) - rows)
                    return False
                else:
                    if offset == selected:
                        offset -= 1
                    selected -= 1
                    return True

        # Helper to determine if a filter matches a description. This is used to filter 
        # items down to a selection with user input.  Treat each word as a individual
        # search term.
        def filter_matches(filter, target):
            if target.always_show:
                return True
            desc = target.orig_desc
            if target.underline:
                desc = desc.replace("[", "").replace("]", "")
            filter = [x.strip() for x in filter.lower().split() if len(x.strip())]
            if len(filter) > 0:
                desc = desc.lower()
                return min(x in desc for x in filter)
            else:
                return True

        # If we have a default option, move the selection to it, using the helper
        # to move the viewport as well
        if default_opt is not None:
            for _ in range(default_opt):
                move_selection(1)

        # And make sure we start off selecting an option that can be selected
        if len(filtered) > 1:
            while filtered[selected].ret is None:
                if not move_selection(1):
                    break

        # Helper to call a callback function
        def call_callback(key=None, override=None):
            nonlocal filtered, filter, selected
            select_item = True
            if filtered[selected].callback is not None:
                temp = {"ret": filtered[selected].ret, "desc": filtered[selected].desc}
                if key is not None:
                    temp["key"] = key

                if override is not None:
                    updated = override
                else:
                    updated = filtered[selected].callback(temp)

                if updated is not None:
                    if callable(updated) or isinstance(updated, dict) and "use_callback" in updated:
                        return updated
                    select_item = False
                    if isinstance(updated, dict):
                        for cur in opts:
                            if cur.ret in updated:
                                cur.desc = updated[cur.ret]
                    else:
                        filtered[selected].desc = updated
                    if len(filter) > 0:
                        # There's a filter, see if the item no longer matches after it changed:
                        if not filter_matches(filter, filtered[selected]):
                            # Ok, we're in an impossible state, reset the filter to leave the user
                            # at a reasonable state
                            filter = ""
                            filtered = [x for x in opts]
                            # Also reset the selected state
                            selected = 0
                            # Select the default item again to start at first principles
                            for i in range(len(filtered)):
                                if filtered[i].default:
                                    selected = i
                                    break
                    trim_descs()
            return select_item

        print_ansi("<hide>", flush=True)
        try:
            # Main display loop
            while True:
                scroll_count = max(1, min(rows - 1, int((rows ** 2) / max(1, len(filtered)))))
                scroll_off = max(0, int((offset / max(1, len(filtered) - rows)) * max(1, rows - scroll_count)))
                output = ""
                # We've already drawn something, move back up to the top and draw over it
                if move_up > 0:
                    output += get_ansi(f"<up {move_up}>")
                    move_up = 0

                for i in range(rows):
                    cur_desc = ""
                    new_len = 0
                    if i+offset < len(filtered):
                        # This is an option inside of the viewport, so show it
                        if i+offset == selected and filtered[i+offset].ret is None:
                            # We selected something that can't be picked, move the selection down
                            selected += 1

                        left = 0
                        picked = False
                        if picked_option is None:
                            if i+offset == selected:
                                # This item is selected, so draw the ">" and "<" chevrons, as well
                                # as inverting the display.  Note, we don't draw the chevrons or 
                                # invert the display if we're running through having picked an
                                # option since that's the final draw cycle, we just want to 
                                # clean up then
                                picked = True
                            elif filtered[i+offset].highlight_next:
                                # If this item highlights with the next, see if the next
                                # should be highlighted too, and run the ramp if there are
                                # more than one in a row
                                extra_offset = 1
                                while True:
                                    if extra_offset+i+offset >= len(filtered):
                                        break
                                    if not filtered[extra_offset+i+offset].highlight_next:
                                        if extra_offset+i+offset == selected:
                                            picked = True
                                        break
                                    extra_offset += 1

                        if picked:
                            cur_desc = filtered[i+offset].pre
                            cur_desc += get_ansi('<invert>') + ">"
                            cur_desc += filtered[i+offset].display
                            cur_desc += " " * (max_desc_len - unicode_len(filtered[i+offset].display))
                            cur_desc += "<" + get_ansi('<revert>')

                            # Store the length, ignoring the ANSI codes
                            new_len = unicode_len(cur_desc) - unicode_len(get_ansi('<invert><revert>'))
                        else:
                            # Normal line, just show the line
                            cur_desc = f"{filtered[i+offset].pre} {filtered[i+offset].display}"
                            new_len = unicode_len(cur_desc)
                            left = max_desc_len - unicode_len(filtered[i+offset].display) + 1

                        if len(filtered) > rows and scroll_bar:
                            new_len += left + 2
                            cur_desc += " " * left
                            if scroll_off <= i <= scroll_count + scroll_off:
                                if i > 0 and i == scroll_off:
                                    cur_desc += " \u25b2" # Up arrow
                                elif i < rows - 1 and i == scroll_count + scroll_off:
                                    cur_desc += " \u25bc" # Down arrow
                                else:
                                    cur_desc += " \u2588" # Solid block
                            else:
                                cur_desc += " \u2502" # Thin line

                    old_disp = shown.get(i, [0, ""])
                    shown[i] = [new_len, cur_desc]
                    if i > 0:
                        # After the first line, we need to move down a line
                        output += "\n"
                        move_up += 1
                    if old_disp[1] != cur_desc:
                        # Only write to the console if the line changed
                        output += cur_desc
                        if old_disp[0] > new_len:
                            # This line is shorter than whatever we last drew on this line, so
                            # draw some spaces on this line to make up for the extra space
                            output += " " * (old_disp[0] - new_len) + "\b" * (old_disp[0] - new_len)
                    output += get_ansi(f"<left {shown[max(shown.keys())][0]}>")
                if picked_option is not None and move_up > 1 and len(filtered) < move_up:
                    # When doing the final pass, go ahead and move up, since we've cleared a bunch of
                    # the screen that we don't need to leave empty
                    output += get_ansi(f"<up {move_up-len(filtered)+(1 if len(filtered) == 0 else 0)}>")
                # We've built up the output, go ahead and send it on out
                print(output, end="", flush=True)

                if picked_option is not None:
                    # All done, just return whatever's picked
                    return picked_option[0]

                x = getkey(getch)

                if DELAY_INPUT:
                    # This will help debug some display issues by pretending to take
                    # one second to process all input
                    import time
                    time.sleep(1.0)

                if x == "enter" or (left_right and wasd and x == "d") or (left_right and x == "right"):
                    # Select the current item
                    select_item = True
                    if len(filtered) > 0 and selected < len(filtered):
                        # If this item has a callback, go ahead and call it
                        select_item = call_callback()
                        if select_item:
                            picked_option = [filtered[selected].ret]
                            temp = filtered[selected]
                            if not temp.keep: # TODO
                                for cur in [temp, temp.header]:
                                    found_item = False
                                    for other in opts[::-1]:
                                        if other == cur or (other.highlight_next and found_item):
                                            found_item = True
                                            other.done_show = True
                                        else:
                                            if found_item:
                                                break
                                filtered = [x for x in opts if x.done_show]
                            filtered = [x for x in filtered if not x.done_hide]
                            for item in filtered:
                                item.pre = ""
                            scroll_bar = False
                            trim_descs()
                    else:
                        # If somehow the user picked nothing, go ahead and treat
                        # it like an escape press
                        picked_option = [None]
                        filtered = [ItemDesc("<no option selected>")]
                    if select_item:
                        selected = 0
                        offset = 0
                elif x == "esc" or (wasd and left_right and x == "a") or (left_right and x == "left"):
                    # Escape was hit, escape the menu
                    filtered = [ItemDesc("<escape pressed>")]
                    selected = -1
                    offset = 0
                    picked_option = [None]
                elif len(x) == 1 and ((not wasd) or (wasd and (x not in {"w", "a", "s", "d", "W", "S"}))) or x == "back":
                    add_to_filter = True
                    if len(filter) == 0 and len(filtered) > 0 and selected < len(filtered) and filtered[selected].any_key:
                        action_callback = call_callback(key=x)
                        need_clear = True

                        if action_callback is not None and isinstance(action_callback, dict):
                            need_clear = action_callback.get("clear", True)
                            action_callback = action_callback["callback"]

                        if action_callback is not None and callable(action_callback):
                            add_to_filter = False

                            if need_clear:
                                clean = ""
                                if move_up > 0:
                                    clean += get_ansi(f"<up {move_up}>")
                                for _ in range(move_up + 1):
                                    clean += " " * (term_width - 1) + "\n"
                                clean = clean.rstrip("\n") + "\b" * (term_width - 1)
                                print(clean + get_ansi("<show>"), end="", flush=True)
                            shown = {}
                            updated_item = action_callback({"ret": filtered[selected].ret, "desc": filtered[selected].desc, "key": x})
                            if need_clear:
                                print(get_ansi("<hide>") + clean, end="", flush=True)
                            call_callback(override=updated_item)
                    if add_to_filter:
                        # Update the filter list
                        if x == "back":
                            filter = filter[:-1]
                        else:
                            filter += x

                        if len(filter) == 0:
                            # Back to no filter, so show all the things
                            filtered = [x for x in opts]
                        else:
                            # We filter down, first trying to find something based off
                            # the line number, otherwise, use the text of the menu item
                            filtered = []
                            if len(filtered) == 0:
                                if filter.lower() in quick_filter:
                                    filtered = [opts[quick_filter[filter.lower()]]]
                            if len(filtered) == 0:
                                # Mark all of the items that the filter matches
                                for x in opts:
                                    x.temp = False
                                    if x.ret is not None:
                                        if filter_matches(filter, x):
                                            x.temp = True
                                # And sweep and mark any item before the marked items that
                                # should be included as well
                                last_marked = False
                                for x in opts[::-1]:
                                    if last_marked:
                                        if x.highlight_next:
                                            x.temp = True
                                        else:
                                            last_marked = False
                                    if not last_marked:
                                        if x.temp:
                                            last_marked = True
                                # Filter down the list to the 
                                filtered = [x for x in opts if x.temp]
                        trim_descs()
                        selected = 0
                        offset = 0
                        # If a multiline item is selected, go ahead and select the final item in the list
                        while len(filtered) > selected and filtered[selected].highlight_next:
                            selected += 1
                elif x == "home":
                    # Move to the top
                    offset = 0
                    selected = 0
                    if len(filtered) > 1:
                        while filtered[selected].ret is None:
                            if not move_selection(1):
                                break
                elif x == "end":
                    # Move to the bottom
                    selected = len(filtered) - 1
                    offset = max(0, len(filtered) - rows)
                    if len(filtered) > 1:
                        while filtered[selected].ret is None:
                            if not move_selection(-1):
                                break
                elif x in {"pageup", "pagedown"} or (wasd and x in {"W", "S"}):
                    # Move the viewport up or down a page
                    if len(filtered) > 1:
                        for _ in range(rows):
                            move_selection(1 if x in {"pagedown", "S"} else -1)
                        while filtered[selected].ret is None:
                            if not move_selection(1 if x in {"pagedown", "S"} else -1):
                                break
                        if filtered[selected].ret is None:
                            while filtered[selected].ret is None:
                                if not move_selection(-1 if x in {"pagedown", "S"} else 1, wrap=False):
                                    break
                elif x in {"up", "down"} or (wasd and x in {"w", "s"}):
                    # Go up or down one item
                    if len(filtered) > 1:
                        move_selection(1 if x in {"down", "s"} else -1, wrap=False)
                        while filtered[selected].ret is None:
                            if not move_selection(1 if x in {"down", "s"} else -1):
                                break
                        if filtered[selected].ret is None:
                            while filtered[selected].ret is None:
                                if not move_selection(-1 if x in {"down", "s"} else 1, wrap=False):
                                    break
        finally:
            # Make sure to turn the cursor back on before we're done
            print_ansi("\n<show>", flush=True)


def test_ui():
    swapping = [
        "1. Alpha (changes to something else)",
        "1. The first greek letter (changes to something else)",
    ]
    # Helper to test the callback functionality, just change the description's case
    def test_callback(data):
        temp = data['desc']
        if data["ret"] == 1:
            if temp == swapping[0]:
                return swapping[1]
            else:
                return swapping[0]
        if temp.upper() == temp:
            if data['ret'] == 4:
                return None
            return temp.lower()
        else:
            return temp.upper()

    # Helper to test that callback for any key works correctly
    def test_edit_callback(data):
        def change_item(data):
            return input("Please enter the new item: ")
        if data.get("key", "") == "e":
            return change_item
        return None

    # Little test to test all the features of this menu.  All of these opts have a 
    # line number in them to make it obvious what's being picked if we test the 
    # mode without line numbers.
    opts = [
        ("--- Some Options with Callbacks ---",),
        {"desc": swapping[0], "ret": 1, "callback": test_callback},
        {"desc": "2. Beta <make sure escapes work>", "ret": 2, "callback": test_callback},
        {"desc": "3. Gamma", "ret": 3, "callback": test_callback},
        {"desc": "4. Delta, this selects when its capital", "ret": 4, "callback": test_callback},
        {"desc": "5. Epsilon goes on and on forever, it really goes on for much longer than two hundred characters, \nit's meant to test out the limits of terminal widths, and make sure that we can handle long strings correctly.", "ret": 5, "callback": test_callback},
        "--- More Options ---",
        ("6. \u6027\u683c\u6d4b\u8bd5 \u6587\u5b57\u30c6\u30b9\u30c8 \uff22\uff29\uff27 Test some fullwidth characters", 6),
        {"desc": "7. Eta (press 'e' on this item to change it)", "ret": 7, "callback": test_edit_callback, "any_key": True},
        ("8. Theta", 8),
        ["9. Iota", 9],
        {"desc": "10. Kappa likes to see the results", "ret": 10, "keep": True},
        {"desc": "11. Lambda likes to [be the] default", "ret": 11, "default": True, "underline": True},
        {"desc": "12. Mu stays when something else is picked", "ret": 12, "done_show": True},
        {"desc": "13. Nu hides when anything else is picked", "ret": 13, "done_hide": True},
        ["14. Xi", 14],
        {"desc": "15. Omicron", "ret": 15, "shortcut": "o"},
        {"desc": "16. Pi", "ret": 16, "shortcut": "p"},
        {"desc": "17. (R)ho", "ret": 17, "shortcut": "r", "hide_shortcut": True},
        ("18. Sigma", 18),
        {"desc": "19. Tau stays even if it should be filtered away", "ret": 19, "always_show": True},
        ("20. Upsilon", 20),
        ("21. Phi", 21),
        {"desc": "22. Chi is a long item that has more than two hundred and forty characters to make sure it wraps on most terminals to test that it's three lines long, it just goes on and on, and never seems to ever really end till it finally does end and stops talking about itself.", "ret": 22, "multiline": 3},
        ("23. Psi", 23),
        ("24. Omega", 24),
        ("--- Even More Options ---", None, "what?"),
        ("25. 10-1 = Receiving poorly", 25),
        ("26. 10-2 = Receiving well", 26),
        ("27. 10-3 = Stop transmitting", 27),
        ("27. The missing message", 28),
        ("29. 10-4 = Message received", 29),
        ("30. 10-5 = Relay message to ___", 30),
        ("31. 10-6 = Busy, please stand by", 31),
        ("32. 10-7 = Out of service, leaving the air", 32),
        ("33. 10-8 = In service, subject to call", 33),
        ("34. 10-9 = Repeat message", 34),
        ("35. 10-10 = Transmission completed, standing by", 35),
        ("36. 10-11 = Talking too rapidly", 36),
        ("37. 10-12 = Visitors present", 37),
        ("38. 10-13 = Advise Weather/Road conditions", 38),
        ("39. 10-16 = Make pick up at ___", 39),
        ("40. 10-17 = Urgent business", 40),
        ("41. 10-18 = Anything for us?", 41),
        ("42. 10-19 = Nothing for you, return to base", 42),
        ("43. 10-20 = My location is _____", 43),
        ("44. 10-21 = Call by telephone", 44),
        ("45. 10-22 = Report in person to", 45),
        ("46. 10-23 = Stand by", 46),
        ("47. 10-24 = Completed last assignment", 47),
        ("48. 10-25 = Can you contact _____", 48),
        ("49. 10-26 = Disregard last information", 49),
        ("50. 10-27 = I am moving to channel ____", 50),
        ("--- And now for some quotes... ---", None),
        ("51. A cow is an ingenious way we humans turn sunlight into steak.", 51),
        ("52. A free society is a place where it's safe to be unpopular.", 52),
        ("53. Anybody remotely interesting is mad, in some way or another.", 53),
        ("54. Anything you might say has already been taken down in evidence against you.", 54),
        ("55. Baseball is the only major sport that appears backwards in a mirror.", 55),
        ("56. Better to light a candle than to curse the darkness.", 56),
        ("57. Better to remain silent and thought a fool than speak up and remove all doubt.", 57),
        ("58. Circular logic will only make you dizzy, Doctor.", 58),
        ("59. Clothes make the man. Naked people have little or no influence on society.", 59),
        ("60. Do things that have never been done before.", 60),
        ("61. Foolproof systems don't take into account the ingenuity of fools.", 61),
        ("62. I am not a member of any organized political party. I am a Democrat.", 62),
        ("63. I don't believe in astrology. I'm a Sagittarius and we're skeptical.", 63),
        ("64. I know life's unfair. But why isn't it ever unfair in my favor?", 64),
        ("65. I love deadlines. I like the whooshing sound they make as they fly by.", 65),
        ("66. I think; therefore I am.", 66),
        ("67. If you build it, he will come.", 67),
        ("68. Inside every cynical person, there is a disappointed idealist.", 68),
        ("69. It's time to kick ass and chew bubble gum ... and I'm all out of gum.", 69),
        ("70. Life begins at the end of your comfort zone.", 70),
        ("71. Logic is the beginning of wisdom; not the end.", 71),
        ("72. Luck is probability taken personally.", 72),
        ("73. Money often costs too much.", 73),
        ("74. Ninety percent of most magic consists of knowing one extra fact.", 74),
        ("75. No Changing on the PremisesNo Biting of Any KindNo Live Snacks", 75),
        ("76. Nobody's perfect. Well, there was this one guy, but we killed him.", 76),
        ("77. Nothing is so permanent as a temporary solution.", 77),
        ("78. Oh that a man's reach should exceed his grasp, or what's a Heaven for?", 78),
        ("79. One drink is just right. Two is too many, and three is not enough.", 79),
        ("80. Peace cannot be kept by force. It can only be achieved by understanding.", 80),
        ("81. The avalanche has already started. It is too late for the pebbles to vote.", 81),
        ("82. The beginning is the most important part of the work.", 82),
        ("83. The devil's cleverest trick is to convince us that he does not exist.", 83),
        ("84. The problem with Internet quotations is that many are not genuine.", 84),
        ("85. There are fewer great satisfactions than that of self.", 85),
        ("86. There is nothing more deceptive than an obvious fact.", 86),
        ("87. They are alone. They are a dying people. We should let them pass.", 87),
        ("88. To the rational mind, nothing is inexplicable; only unexplained.", 88),
        ("89. Today was a classic Seattle day. It didn't rain. It didn't not rain.", 89),
        ("90. Under capitalism, man exploits man. Under communism, it's just the opposite.", 90),
        ("91. Verbing weirds language.", 91),
        ("92. We are the universe, trying to understand itself.", 92),
        ("93. What do you despise? By this are you truly known.", 93),
        ("94. What do you know about hell? Would you like me to show it to you?", 94),
        ("95. When the gods choose to punish us, they merely answer our prayers.", 95),
        ("96. You speak treason! Fluently!", 96),
        ("97. Your theory is crazy, but it's not crazy enough to be true.", 97),
    ]

    def get_input(value, default):
        x = input(value)
        if isinstance(default, bool):
            if x.lower() == "y": return True
            elif x.lower() == "n": return False
        elif isinstance(default, int):
            if len(x) > 0: return int(x)
        return default
    args = {
        "line_numbers": get_input("Show line numbers [(y)/n]: ", True),
        "keep_header": get_input("Keep headers [y/(n)]: ", False),
        "scroll_bar": get_input("Show scroll bar [(y)/n]: ", True),
        "max_rows": get_input("Max number of rows [-1]: ", -1),
        "wasd": get_input("Use WASD as arrow keys [y/(n)]: ", False),
    }
    global DELAY_INPUT
    DELAY_INPUT = get_input("Delay all input by 1 second (aka, DELAY_INPUT) [y/(n)]: ", False)

    x = list_picker(opts, **args)
    print(f"You picked {x}!")


if __name__ == "__main__":
    test_ui()
