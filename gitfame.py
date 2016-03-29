#!/usr/bin/env python
r"""
Usage:
  gitfame [--help | options] [<gitdir>]

Options:
  -h, --help     Print this help and exit.
  -v, --version  Print module version and exit.
  --sort=<key>   Options: [default: loc], files, commits.
  --exclude-files=<f>      Comma-separated list [default: None].
                           Escape (\,) for a literal comma
                           (may require \\, in shell).
  -r, --regex              Assume <f> are comma-separated regular expressions
                           rather than exact matches [default: false].
  -s, --silent-progress    Suppress `tqdm` [default: False].
  -t, --bytype             Show stats per file extension [default: False].
  -w, --ignore-whitespace  Ignore whitespace when comparing the parent's
                           version and the child's to find where the lines
                           came from [default: False].
Arguments:
  <gitdir>       Git directory [default: ./].
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import subprocess
import re
from _utils import TERM_WIDTH, int_cast_or_len, Max, fext
from tqdm import tqdm

__author__ = "Casper da Costa-Luis <casper@caspersci.uk.to>"
__date__ = "2016"
__licence__ = "[MPLv2.0](https://mozilla.org/MPL/2.0/)"
__all__ = ["main"]
__copyright__ = ' '.join((__author__, "(c)", __date__, __licence__))
__license__ = __licence__  # weird foreign language


RE_AUTHS = re.compile('^author (.+)$', flags=re.M)
# finds all non-escaped commas
# NB: does not support escaping of escaped character
RE_CSPILT = re.compile(r'(?<!\\),')
RE_NCOM_AUTH_EM = re.compile(r'^\s*(\d+)\s+(.*)\s+<(.*)>\s*$', flags=re.M)


def tr_hline(col_widths, hl='-', x='+'):
  return x + x.join(hl * i for i in col_widths) + x


def tabulate(auth_stats, stats_tot, args_sort="loc", args_bytype=False):
  res = ''
  # Columns: Author | loc | coms | fils | distribution
  COL_LENS = [
      max(6, Max(len(a.decode('utf-8')) for a in auth_stats)),
      max(3, Max(len(str(stats["loc"]))
                 for stats in auth_stats.itervalues())),
      max(4, Max(len(str(stats.get("commits", 0)))
                 for stats in auth_stats.itervalues())),
      max(4, Max(len(str(len(stats.get("files", []))))
                 for stats in auth_stats.itervalues())),
      12
  ]

  COL_LENS[0] = min(TERM_WIDTH - sum(COL_LENS[1:]) - len(COL_LENS) * 3 - 3,
                    COL_LENS[0])

  COL_NAMES = [
      "Author" + ' ' * (COL_LENS[0] - 6),
      ' ' * (COL_LENS[1] - 3) + "loc",
      ' ' * (COL_LENS[2] - 4) + "coms",
      ' ' * (COL_LENS[3] - 4) + "fils",
      " distribution "
  ]

  tbl_row_fmt = "| {0:<%ds}| {1:>%dd} | {2:>%dd} | {3:>%dd} |" \
                " {4:4.1f}/{5:4.1f}/{6:4.1f} |" % (COL_LENS[0] + 1,
                                                   COL_LENS[1],
                                                   COL_LENS[2],
                                                   COL_LENS[3])

  TR_HLINE = tr_hline([len(i) + 2 for i in COL_NAMES])
  res += TR_HLINE + '\n'
  res += ("| {0:s} | {1:s} | {2:s} | {3:s} | {4} |").format(*COL_NAMES) + '\n'
  res += tr_hline([len(i) + 2 for i in COL_NAMES], '=') + '\n'

  for (auth, stats) in tqdm(sorted(auth_stats.iteritems(),
                                   key=lambda k: int_cast_or_len(
                                       k[1].get(args_sort, 0)),
                                   reverse=True), leave=False):
    # print (stats)
    loc = stats["loc"]
    commits = stats.get("commits", 0)
    files = len(stats.get("files", []))
    # TODO:
    # if args_bytype:
    #   print ([stats.get("files", []) ])
    res += (tbl_row_fmt.format(
        auth[:len(COL_NAMES[0]) + 1], loc, commits, files,
        100 * loc / max(1, stats_tot["loc"]),
        100 * commits / max(1, stats_tot["commits"]),
        100 * files / max(1, stats_tot["files"])).replace('100.0', ' 100')) \
        + '\n'
    # TODO: --bytype
  return res + TR_HLINE


def run(args):
  """ args: dict (docopt format) """

  if args["<gitdir>"] is None:
    args["<gitdir>"] = './'
    # sys.argv[0][:sys.argv[0].replace('\\','/').rfind('/')]

  if args["--sort"] not in ["loc", "commits", "files"]:
    raise(Warning("--sort argument unrecognised\n" + __doc__))

  if not args["--exclude-files"]:
    args["--exclude-files"] = ""

  gitdir = args["<gitdir>"].rstrip(r'\/').rstrip('\\')
  git_cmd = ["git", "--git-dir", gitdir + "/.git", "--work-tree", gitdir]
  exclude_files = RE_CSPILT.split(args["--exclude-files"])

  file_list = subprocess.check_output(git_cmd +
                                      ["ls-files"]).strip().split('\n')
  RE_EXCL = None
  if args['--regex']:
    RE_EXCL = re.compile('|'.join(i for i in exclude_files), flags=re.M)

  # finished parsing args

  auth_stats = {}

  for fname in tqdm(file_list, desc="Blame", disable=args["--silent-progress"]):
    if RE_EXCL.search(fname) if args['--regex'] else (fname in exclude_files):
      continue

    git_blame_cmd = git_cmd + ["blame", fname, "--line-porcelain"]
    if args["--ignore-whitespace"]:
      git_blame_cmd.append("-w")
    try:
      blame_out = subprocess.check_output(git_blame_cmd,
                                          stderr=subprocess.STDOUT)
    except:
      continue
    auths = RE_AUTHS.findall(blame_out)

    for auth in auths:
      try:
        auth_stats[auth]["loc"] += 1
      except KeyError:
        auth_stats[auth] = {"loc": 1, "files": set([fname])}
      else:
        auth_stats[auth]["files"].add(fname)

      if args["--bytype"]:
        fext_key = ("." + fext(fname)) if fext(fname) else "._None_ext"
        # auth_stats[auth].setdefault(fext_key, 0)
        try:
          auth_stats[auth][fext_key] += 1
        except KeyError:
          auth_stats[auth][fext_key] = 1

  # print (auth_stats.keys())
  auth_commits = subprocess.check_output(git_cmd + ["shortlog", "-s", "-e"])
  for stats in auth_stats.itervalues():
    stats.setdefault("commits", 0)
  # print (RE_NCOM_AUTH_EM.findall(auth_commits.strip()))
  for (ncom, auth, _) in RE_NCOM_AUTH_EM.findall(auth_commits.strip()):
    try:
      auth_stats[auth]["commits"] += int(ncom)
    except KeyError:
      # pass
      auth_stats[auth] = {"loc": 0, "files": set([]), "commits": int(ncom)}

  stats_tot = dict((k, 0) for stats in auth_stats.itervalues() for k in stats)
  # print (stats_tot)
  for k in stats_tot:
    stats_tot[k] = sum(int_cast_or_len(stats.get(k, 0))
                       for stats in auth_stats.itervalues())

  extns = set()
  if args["--bytype"]:
    for stats in auth_stats.itervalues():
      extns.update([fext(i) for i in stats["files"]])
  # print (extns)

  print ('Total ' + '\nTotal '.join("{0:s}: {1:d}".format(k, v)
         for (k, v) in sorted(stats_tot.iteritems())))

  print (tabulate(auth_stats, stats_tot, args["--sort"]))


def main():
  from docopt import docopt
  args = docopt(__doc__ + '\n' + __copyright__, version="0.9.0")
  # raise(Warning(str(args)))

  run(args)


if __name__ == "__main__":
  main()
