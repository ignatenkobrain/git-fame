import sys
__author__ = "Casper da Costa-Luis <casper@caspersci.uk.to>"
__date__ = "2016"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["TERM_WIDTH", "int_cast_or_len", "Max", "fext", "_str"]
__copyright__ = ' '.join((__author__, __date__, __licence__))
__license__ = __licence__  # weird foreign language


def _str(s):
  try:
    return s.decode(encoding='utf-8')
  except:
    return s


def fext(fn):
  """
  >>> fext('foo/bar.baz')
  'baz'
  >>> fext('foo/.baz')
  'baz'
  >>> fext('foo/bar')
  ''

  """
  res = fn.split('.')
  return res[-1] if len(res) > 1 else ''


def _environ_cols_windows(fp):  # pragma: no cover
  try:
    from ctypes import windll, create_string_buffer
    import struct
    from sys import stdin, stdout

    io_handle = None
    if fp == stdin:
      io_handle = -10
    elif fp == stdout:
      io_handle = -11
    else:  # assume stderr
      io_handle = -12

    h = windll.kernel32.GetStdHandle(io_handle)
    csbi = create_string_buffer(22)
    res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
    if res:
      (bufx, bufy, curx, cury, wattr, left, top, right, bottom,
       maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
      # nlines = bottom - top + 1
      return right - left  # +1
  except:
    pass
  return None


def _environ_cols_tput(*args):  # pragma: no cover
  """ cygwin xterm (windows) """
  try:
    import subprocess
    import shlex
    cols = int(subprocess.check_call(shlex.split('tput cols')))
    # rows = int(subprocess.check_call(shlex.split('tput lines')))
    return cols
  except:
    pass
  return None


def _environ_cols_linux(fp):  # pragma: no cover

  # import os
  # if fp is None:
  #   try:
  #     fp = os.open(os.ctermid(), os.O_RDONLY)
  #   except:
  #     pass
  try:
    from termios import TIOCGWINSZ
    from fcntl import ioctl
    from array import array
  except ImportError:
    return None
  else:
    try:
      return array('h', ioctl(fp, TIOCGWINSZ, '\0' * 8))[1]
    except:
      try:
        from os.environ import get
      except ImportError:
        return None
      else:
        return int(get('COLUMNS', 1)) - 1


def _environ_cols_wrapper():  # pragma: no cover
  """
  Return a function which gets width and height of console
  (linux,osx,windows,cygwin).

  Based on https://raw.githubusercontent.com/tqdm/tqdm/master/tqdm/_utils.py
  """
  import platform
  current_os = platform.system()
  _environ_cols = None
  if current_os in ['Windows', 'cli']:
    _environ_cols = _environ_cols_windows
    if _environ_cols is None:
      _environ_cols = _environ_cols_tput
  if any(current_os.startswith(i) for i in
         ['CYGWIN', 'MSYS', 'Linux', 'Darwin', 'SunOS', 'FreeBSD']):
    _environ_cols = _environ_cols_linux
  return _environ_cols


TERM_WIDTH = _environ_cols_wrapper()(sys.stdout)


def int_cast_or_len(i):
  """
  >>> int_cast_or_len(range(10))
  10
  >>> int_cast_or_len('90 foo')
  6
  >>> int_cast_or_len('90')
  90

  """
  try:
    return int(i)
  except:
    return len(i)


def Max(it, empty_default=0):
  """
  >>> Max(range(10), -1)
  9
  >>> Max(range(0), -1)
  -1

  """
  try:
    return max(it)
  except ValueError as e:
    if 'empty sequence' in str(e):
      return empty_default
    raise