#!/usr/bin/env python
#
#                                                                        DRAGONS
#
#                                                                     swapper.py
# ------------------------------------------------------------------------------
__version__  = '2.0'
# ------------------------------------------------------------------------------
#
#    functional tasks
#
# -- sift through each module, searching for input 'string'
# -- report each found line, showing current current line
# -- report the matching line with it's new string insert.
# -- user approves line swap OR edits file. In auto mode, 
#    line swapping proceeds.
# -- report all swapped lines to log, indicate line #
#
# Faces will show highlights on terminal out, but will look a mess in log
# (escape chars, color codes). more the log to get highlighting text.
#
# $ swapper -h
# usage: swapper [-h] [-a] [-c] [-d] [-f] [-r] [-l LOGNAME] [-m MODULE]
#                [-u USERPATH]
#                ostring nstring
#
# positional arguments:
#   ostring      <old_string>
#   nstring      <new_string>
#
# optional arguments:
#   -h, --help   show this help message and exit
#   -a, --auto   Execute swaps without user confirmation. Default is False. User
#                must request auto execute
#   -c           Switch on color high lighting. Default is Off.
#   -d           Document line changes w/ swapper comments.
#   -f           Search FitsStorage package.
#   -l LOGNAME   Set the logfile name. Default is 'swap.log'.
#   -m MODULE    Execute swaps in <module> only. Default is all.
#   -r           Report potential swaps only. Default is 'False'.
#   -u USERPATH  Use this path to build search paths. Default is None. Without
#                -u, search under $GEM.
# ------------------------------------------------------------------------------
desc = """
Description:
  swapper replaces string literals that occur within defined DRAGONS packages.
  These packages are

    astrodata/
    gemini_instruments/
    geminidr/
    gempy/
    recipe_system/

  Search paths are based upon an environment variable, $DRAGONS, OR on the path
  passed with the '-u USERPATH' option. $DRAGONS defines a path to a user's
  DRAGONS installation as pulled from the GDPSG GitHub repository, and which
  nominally contains the 'branches' and 'trunk' directories as they appear 
  in the DRAGONS repo. I.e.,

    export DRAGONS=/user/path/to/dragons

  If a user has a non-standard or partial DRAGONS installation, or has 
  otherwise changed the above organisation, the -u option should be used to 
  pass the location of this code base to swapper. If -u is passed, search 
  packages should be directly under this path.

  Examples:

  -- a standard DRAGONS repo checkout in ~ :

      $ export DRAGONS=~/dragons
      $ swapper -c -r "old string" "new string"

  -- astrodata, gempy, and other DRAGONS packages are in directory
     ~/foobar/. Use -u:

      $ swapper -r -c -u ~/foobar "old string" "new string"

  swapper can search the trunk of the FitsStorage code base, provided it is
  installed. Search paths are based upon an environment variable, $FITSSTORE,
  which currently is held in an svn repo.

  The $FITSSTORE env var should be defined to include the trunk or branch of the
  repository a user wishes to search.

  E.g.,

  export FITSSTORE=/path/to/fitsstore/trunk

  or using a branch name,

  export FITSSTORE=/path/to/fitsstore/branch/2017-1

  Users must use the '-f' option on the swapper command to search the code base 
  defined by $FITSSTORE.

"""
import os
import sys
import glob
import shlex
import fileinput
import subprocess

from time import strftime
from shutil import copyfile
from os.path import basename, exists, join, split
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from gempy.utils import logutils

# ------------------------------------------------------------------------------
dragons_set = {"apaths":
               [ 'astrodata',
                 'gemini_instruments',
                 'gemini_instruments/bhros',
                 'gemini_instruments/cirpass',
                 'gemini_instruments/f2',
                 'gemini_instruments/flamingos',
                 'gemini_instruments/gemini',
                 'gemini_instruments/gmos',
                 'gemini_instruments/gnirs',
                 'gemini_instruments/gpi',
                 'gemini_instruments/graces',
                 'gemini_instruments/gsaoi',
                 'gemini_instruments/hokupaa_quirc',
                 'gemini_instruments/hrwfs',
                 'gemini_instruments/igrins',
                 'gemini_instruments/michelle',
                 'gemini_instruments/nici',
                 'gemini_instruments/nifs',
                 'gemini_instruments/niri',
                 'gemini_instruments/phoenix',
                 'gemini_instruments/skycam',
                 'gemini_instruments/test',
                 'gemini_instruments/trecs'
               ],
               "gdr_paths":
               [ 'geminidr',
                 'geminidr/core',
                 'geminidr/f2',
                 'geminidr/f2/lookups',
                 'geminidr/f2/recipes/qa',
                 'geminidr/f2/recipes/sq',
                 'geminidr/gemini',
                 'geminidr/gemini/lookups',
                 'geminidr/gmos',
                 'geminidr/gmos/lookups',
                 'geminidr/gmos/recipes/qa',
                 'geminidr/gmos/recipes/sq',
                 'geminidr/gnirs',
                 'geminidr/gnirs/lookups',
                 'geminidr/gnirs/recipes/qa',
                 'geminidr/gnirs/recipes/sq',
                 'geminidr/gsaoi',
                 'geminidr/gsaoi/lookups',
                 'geminidr/gsaoi/recipes/qa',
                 'geminidr/gsaoi/recipes/sq',
                 'geminidr/niri',
                 'geminidr/niri/lookups',
                 'geminidr/niri/recipes/qa',
                 'geminidr/niri/recipes/sq',
               ],
               "rpaths":
               [ 'recipe_system',
                 'recipe_system/adcc',
                 'recipe_system/adcc/servers',
                 'recipe_system/cal_service',
                 'recipe_system/mappers',
                 'recipe_system/reduction',
                 'recipe_system/scripts',
                 'recipe_system/utils',
               ],
               "gpaths":
               [ 'gempy/adlibrary',
                 'gempy/eti_core',
                 'gempy/gemini',
                 'gempy/gemini/eti',
                 'gempy/gemini/eti/tests',
                 'gempy/gemini/tests',
                 'gempy/library',
                 'gempy/library/config',
                 'gempy/library/tests',
                 'gempy/mosaic',
                 'gempy/mosaic/tests/mosaic',
                 'gempy/scripts',
                 'gempy/utils',
               ],
}

fits_set = { 'db_paths':
             [ 'dbmigration',
	       'dbmigration/versions'
             ],
             'fits_paths' :
             [ 'fits_storage',
               'fits_storage/cal',
               'fits_storage/orm',
               'fits_storage/scripts/',
               'fits_storage/utils',
               'fits_storage/utils/web',
               'fits_storage/web'
             ],
             'test_paths':
             [ 'test',
               'test/orm',
               'test/utils',
               'test/web'
             ],
             'userc_paths': ['user-clients']
}

# ------------------------------------------------------------------------------
def handleCLArgs():
    parser = ArgumentParser(description=desc, prog='swapper',
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('ostring', help="<old_string>")
    parser.add_argument('nstring', help="<new_string>")

    parser.add_argument("-a", "--auto", dest="auto", action="store_true",
                        help="Execute swaps without user confirmation."
                        " Default is False. User must request auto execute")

    parser.add_argument("-c", dest="color", action="store_true",
                        help="Switch on color high lighting."
                        " Default is Off.")

    parser.add_argument("-d", dest="doc", action="store_true",
                        help="Document line changes w/ swapper comments.")

    parser.add_argument("-f", dest="fitss", action="store_true",
                        help="Search FitsStorage package.")

    parser.add_argument("-m", dest="module", default=None,
                        help="Execute swaps in <module> only."
                        " Default is all.")

    parser.add_argument("-r", dest="report", action="store_true",
                        help="Report potential swaps only."
                        " Default is 'False'.")

    parser.add_argument("-u", dest="userpath", default=None,
                        help="Use this path to build search paths."
                        " Default is None. Without -u, search under $NGEM. ")

    parser.add_argument("-v", '--version', action='version', 
                        version='%(prog)s ' + __version__)

    args = parser.parse_args()
    return args

# ------------------------------------------------------------------------------
# Faces class
# -- set stdout face symbols
# Eg.,
#
# print Faces.BOLD + 'Hello World !' + Faces.END

class Faces(object):
    PURPLE    = '\033[95m'
    CYAN      = '\033[96m'
    DARKCYAN  = '\033[36m'
    BLUE      = '\033[94m'
    GREEN     = '\033[92m'
    YELLOW    = '\033[93m'
    RED       = '\033[91m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    END       = '\033[0m'

# ------------------------------------------------------------------------------
class Swap(object):

    def __init__(self, args):
        """
        Instance definitions.

        Parameters:
        ----------
        args : <Namespace>
               An argparse namespace object or one that provides an equivalent
               interface.

        """
        self.DRAGONS  = None
        self.FITS     = None
        self.auto_run = args.auto
        self.colorize = args.color
        self.cur_str  = args.ostring
        self.doc      = args.doc
        self.focus    = args.module
        self.new_str  = args.nstring
        if args.userpath:
            self.userpath = os.path.abspath(args.userpath)
        else:
            self.userpath = args.userpath

        self.pymods = []
        self.full_paths = []
        self.swap_summary = ()
        self.search_fits = args.fitss
        self.search_root = None
        self.search_set = None

    def setup_search(self):
        if self.userpath:
            self.search_root = self.userpath
        elif self.search_fits:
            try:
                self.search_root = os.path.abspath(os.environ['FITSSTORE'])
            except KeyError:
                pass
            self.search_set = fits_set
        else:
            try:
                self.search_root = os.path.abspath(os.environ['DRAGONS'])
            except KeyError:
                pass
            self.search_set = dragons_set

        if self.search_set is None:
            msg = "Specify -u USERPATH OR define $DRAGONS OR define $FITS. "
            msg += "-h for help."
            raise SystemExit(msg)

        return

    def set_search_paths(self):
        for pathkey in list(self.search_set.keys()):
            for path in self.search_set[pathkey]:
                self.full_paths.append(join(self.search_root, path))

        return

    def set_searchable_mods(self):
        """ Builds the set of searchable modules in all paths."""
        for path in self.full_paths:
            py_modules = self._get_py_modules(path)
            self.pymods.extend(py_modules)
        return

    def report(self):
        """
        Report *only* matches found in modules. Called when user specifies
        -r switch.

        """
        new_head = ""
        self._echo_header()
        for mod in self.pymods:
            mod_test = basename(mod)
            if self.focus and not mod_test == self.focus:
                continue
            match_lines = []
            fpath, tail  = os.path.split(mod)
            head = fpath.split(self.search_root)[-1]
            match_lines = self._search_and_report(mod, self.cur_str)
            if match_lines:
                if head != new_head:
                    new_head = head
                    log.stdinfo(Faces.YELLOW + "\n------------" + Faces.END)
                    log.stdinfo("@ " + Faces.DARKCYAN + new_head + ":" + Faces.END)
                for line in match_lines:
                    log.stdinfo(Faces.BOLD + tail + Faces.END + line)
        return

    def report_and_execute(self):
        """
        Method will discover matched lines as in .report(), but will 
        display what the new line will look like upon substitution. 
        User confirmation is required to execute the swap unless 
        -a, --auto has been specified.
        """
        nmods  = 0
        nswaps = 0
        new_head = ""
        current_mod = None
        self._echo_header()
        for mod in self.pymods:
            mod_test = basename(mod)
            if self.focus and not mod_test == self.focus:
                continue
            match_lines = []
            fpath, tail = os.path.split(mod)
            head = fpath.split(self.search_root)[-1]
            match_lines = self._search_for_execute(mod, self.cur_str, self.new_str)
            if match_lines:
                current_mod = mod
                if head != new_head:
                    new_head = head
                    log.stdinfo(Faces.YELLOW + "\n------------" + Faces.END)
                    log.stdinfo("@ " + Faces.DARKCYAN + new_head + ":" + Faces.END)
                for line_set in match_lines:
                    log.stdinfo(Faces.BOLD + tail + Faces.END + line_set[1])
                    log.stdinfo(Faces.BOLD + tail + Faces.END + line_set[3])
                    if self.auto_run:
                        if current_mod == mod:
                            nmods  += 1
                        nswaps += 1
                        self._execute_swap(mod, line_set)
                    else:
                        if self._confirm_swap(mod, line_set[0] + 1):
                            if current_mod == mod:
                                pass
                            else:
                                current_mod = mod
                                nmods += 1
                            nswaps += 1
                            log.stdinfo("Swap confirmed.")
                            self._execute_swap(mod, line_set)
                        else:
                            continue
        if nswaps and nmods:
            self.swap_summary = (nswaps, nmods)
        return

    def summarize(self):
        if self.swap_summary:
            swaps, mods = self.swap_summary
            log.stdinfo(Faces.YELLOW + "------------" + Faces.END)
            log.stdinfo("\n%s swap(s) executed in %s module(s)" % 
                        (str(swaps), str(mods)))
            log.stdinfo("\tNote: User edits are not tallied")
        return

    
    # ------------------------------ prive -------------------------------------
    def _echo_header(self):
        root_name = os.path.split(self.search_root)[-1]
        if root_name == 'trunk':
            root_name = os.path.split(os.path.split(self.search_root)[-2])[-1]
        log.stdinfo("\n" + basename(__file__) + " \t" + __version__)
        log.stdinfo("SEARCHING\t" + Faces.BOLD + root_name.upper()+" ... "+Faces.END)
        return

    def _determine_gem_path(self):
        """ Build the instance gem_path variable. """
        gem_path = None
        if not self.userpath and not self.DRAGONS and not self.FITS:
            msg = "Specify -u USERPATH OR define $DRAGONS OR define $FITS. "
            msg += "-h for help."
            raise SystemExit(msg)

        # Override gem_path if userpath has been specified.
        if self.userpath:
            gem_path = self.userpath
        elif self.FITS:
            gem_path = self.FITS
        elif self.DRAGONS:
            gem_path = self.DRAGONS

        return gem_path

    def _get_py_modules(self, path):
        """ Return a list of python modules in the passed path.

        parameters: <str>
        return:     <list>
        """
        return glob.glob(join(path, "*.py"))

    def _search_and_report(self, module, string):
        match_lines = []
        mod_lines = open(module).readlines()

        for i in range(len(mod_lines)):
            line = mod_lines[i].strip()
            sindex = line.find(string)
            eindex = sindex + len(string)
            if sindex > -1:
                if self.colorize:
                    matched_line = self._build_electric_line(line, i, sindex, eindex)
                else:
                    matched_line = self._build_vanilla_line(line, i, sindex, eindex)
                match_lines.append(matched_line)
        return match_lines

    def _search_for_execute(self, module, ostring, nstring):
        swap_lines = []
        open_mod  = open(module)
        mod_lines = open_mod.readlines()
        open_mod.close()

        for i in range(len(mod_lines)):
            line = mod_lines[i].rstrip()
            sindex = line.find(ostring)
            eindex = sindex + len(ostring)
            if sindex > -1:
                if self.colorize:
                    matched_line = self._build_electric_line(line, i, sindex, eindex)
                    new_line, print_line = self._build_electric_new_line(line, i,
                                                                         sindex,
                                                                         ostring,
                                                                         nstring)
                else:
                    matched_line = self._build_vanilla_line(line, i, sindex, eindex)
                    new_line, print_line  = self._build_vanilla_new_line(line, i,
                                                                         sindex,
                                                                         ostring,
                                                                         nstring)

                swap_lines.append((i, matched_line, new_line, print_line))
        return swap_lines

    def _build_electric_line(self, line, i, sindex, eindex):
        """ Build electric line, high lighting various parts.

        parameters: <int>, <int>, <int>, indices: line, string match start, end
        return:     <str>, string with highlighting escape chars.
        """
        electric_line = (Faces.CYAN + "@L" + str(i + 1) + "::  " + Faces.END 
                         + line[:sindex] + Faces.RED + line[sindex:eindex] 
                         + Faces.END + line[eindex:])

        return electric_line

    def _build_vanilla_line(self, line, i, sindex, eindex):
        """ Build vanilla line, no high lighting.

        parameters: <int>, <int>, <int>, indices: line, start string match, end
        return:     <str>, string with highlighting escape chars.
        """
        vanilla_line = ("@L" + str(i + 1) + "::  " + line[:sindex] + 
                         line[sindex:eindex] + line[eindex:])
        return vanilla_line

    def _build_electric_new_line(self, line, i, sindex, ostring, nstring):
        """ Build electric line, high lighting various parts.

        parameters: <str>, <int>, <int>, <str>, <str> 
                    line, lineno, str index start, end, old str, new str
        return:     <str>, string with highlighting escape chars.
        """
        line = line.replace(ostring, nstring)
        eindex = sindex + len(nstring)
        electric_line = (Faces.CYAN + "@L" + str(i + 1) + "::  " + Faces.END 
                         + line[:sindex] + Faces.RED + line[sindex:eindex] 
                         + Faces.END + line[eindex:] + Faces.CYAN +"\t <== NEW"
                         + Faces.END)
        return line, electric_line

    def _build_vanilla_new_line(self, line, i, sindex, ostring, nstring):
        """ Build vanilla line, no high lighting.

        parameters: <str>, <int>, <int>, <str>, <str> 
                    line, string index start, end, old string, new string
        return:     <str>, string with highlighting escape chars.
        """
        line = line.replace(ostring, nstring)
        eindex = sindex + len(nstring)
        vanilla_line = ("@L" + str(i + 1) + "::  " + line[:sindex] + 
                         line[sindex:eindex] + line[eindex:] + "\t <== NEW")
        return line, vanilla_line

    def _confirm_swap(self, mod, lineno):
        confirm = False
        try:
            response = input("\nConfirm swap (y/n/e): ")
            if response == "y":
                confirm = True
            elif response == "e":
                self._user_edit_mode(mod, lineno)
        except KeyboardInterrupt:
            sys.exit("\tExiting on ^C\n")
        return confirm

    def _execute_swap(self, mod, line_set):
        """ Execute approved line swap. line_set is a tuple comprising
        the match (current) line, the computed new line, and the built
        printable line (unused here).

        mod      --  module name, which is a full path
        line_set --  tuple of values, where index is the index of the line
                     in the list of lines of the module.

        parameters: <str>, <tuple>, file, index, old line, new line, printer
        return:     <void>
        """
        lineno   = line_set[0] + 1
        if self.doc:
            comment  = " # Changed by swapper, " + strftime("%d %b %Y") + "\n"
        else:
            comment = "\n"
        new_line = line_set[2] + comment

        log.stdinfo("Executing swap in module: " +  basename(mod))
        log.stdinfo(Faces.CYAN + "New line @L" + str(lineno) + ":: " + 
                    Faces.END + new_line)
        for line in fileinput.input(mod, inplace=1, backup=".bak"):
            if fileinput.filelineno() == lineno:
                line = new_line
            sys.stdout.write(line)
        fileinput.close()
        return

    def _user_edit_mode(self, mod, lineno):
        cmd = "emacs +" + "%s %s" % (str(lineno), mod)
        args = shlex.split(cmd)
        subprocess.call(args)
        return

# ------------------------------------------------------------------------------
def main(args):
    swap = Swap(args)
    swap.setup_search()
    swap.set_search_paths()
    swap.set_searchable_mods()
    if args.report:
        swap.report()
    else:
        swap.report_and_execute()
        swap.summarize()
    return

# ____________________
if __name__ == "__main__":
    args = handleCLArgs()
    logutils.config(file_name='swap.log')
    log = logutils.get_logger(__name__)
    sys.exit(main(args))
