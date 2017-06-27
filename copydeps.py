#!/usr/bin/env python3
import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys


__appname__ = 'copydeps'
__version__ = '1.0.0'
__license__ = 'Apache 2.0'

DESCRIPTION = """\
Copy dependencies required by an executable to the specified dir. Dependencies
can be blacklisted. If a library is blacklisted then all its dependencies are
blacklisted unless a non-blacklisted library depend on them.
"""

# Black list Linux dynamic loaders by default because they do not fit in the
# soname => path output of ldd
DEFAULT_BLACKLIST = ['ld-linux.so.*', 'ld-linux-x86-64.so.*']

DOT_BLACKLISTED_ATTRS = '[color="gray" fontcolor="gray"]'


def load_blacklist(filename):
    with open(filename, 'rt') as f:
        for line in f.readlines():
            line = line.strip()
            if not line or line[0] == '#':
                continue
            yield line


def list_soname_paths(executable):
    """Return a dict of the form soname => path"""
    out = subprocess.check_output(('ldd', executable))

    dct = {}
    for line in out.splitlines():
        line = line.strip().decode('ascii')
        # line can be one of:
        # 1. linux-vdso.so.1 =>  (0x00007ffd6f3cd000)
        # 2. libcrypto.so.1.0.0 => /home/agateau/tmp/genymotion/./libcrypto.so.1.0.0 (0x00007f5ea40b6000)
        # 3. /lib64/ld-linux-x86-64.so.2 (0x0000562cf1094000)

        if '=>  (' in line:
            # Format #1, skip it
            continue
        if '=>' not in line:
            # Format #3, skip it. Only Linux dynamic loaders seem to use it
            continue

        # Format #2
        tokens = line.split(' ', 3)
        assert tokens[1] == '=>', 'Unexpected line format: {}'.format(line)

        soname = tokens[0]

        # Handle the case where a library has not been found
        assert tokens[2:4] != ['not', 'found'], 'No path for {}'.format(soname)

        path = tokens[2]
        dct[soname] = path
    return dct


def list_dependencies(binary):
    """Return the list of sonames this binary *directly* depends on"""

    # We use `readelf` to get the soname list. Its output looks like this:
    #
    # Dynamic section at offset 0xf79d0 contains 34 entries:
    #   Tag        Type                         Name/Value
    #  0x0000000000000001 (NEEDED)             Shared library: [libz.so.1]
    #  0x0000000000000001 (NEEDED)             Shared library: [libminicrypt.so.1]
    #  0x0000000000000001 (NEEDED)             Shared library: [libQt5Widgets.so.5]
    #  0x0000000000000001 (NEEDED)             Shared library: [libQt5Gui.so.5]
    #  0x0000000000000001 (NEEDED)             Shared library: [libQt5Network.so.5]
    #  0x0000000000000001 (NEEDED)             Shared library: [libQt5Script.so.5]
    #  0x0000000000000001 (NEEDED)             Shared library: [libQt5Sql.so.5]
    #  0x0000000000000001 (NEEDED)             Shared library: [libQt5Core.so.5]
    #  0x0000000000000001 (NEEDED)             Shared library: [libpthread.so.0]
    #  0x0000000000000001 (NEEDED)             Shared library: [libstdc++.so.6]
    #  0x0000000000000001 (NEEDED)             Shared library: [libgcc_s.so.1]
    #  0x0000000000000001 (NEEDED)             Shared library: [libc.so.6]
    #  0x000000000000000f (RPATH)              Library rpath: [$ORIGIN:/home/buildbot/Qt5.4.1/5.4/gcc_64:/home/buildbot/Qt5.4.1/5.4/gcc_64/lib]
    #  0x000000000000000c (INIT)               0x40fef0
    #  0x000000000000000d (FINI)               0x4ca078
    #  0x0000000000000019 (INIT_ARRAY)         0x6f51c0
    #  0x000000000000001b (INIT_ARRAYSZ)       296 (bytes)
    #  0x000000006ffffef5 (GNU_HASH)           0x400298
    #  0x0000000000000005 (STRTAB)             0x404ee8
    #  0x0000000000000006 (SYMTAB)             0x400ac0
    #  0x000000000000000a (STRSZ)              24298 (bytes)
    #  0x000000000000000b (SYMENT)             24 (bytes)
    #  0x0000000000000015 (DEBUG)              0x0
    #  0x0000000000000003 (PLTGOT)             0x6f7fe8
    #  0x0000000000000002 (PLTRELSZ)           14208 (bytes)
    #  0x0000000000000014 (PLTREL)             RELA
    #  0x0000000000000017 (JMPREL)             0x40c770
    #  0x0000000000000007 (RELA)               0x40b450
    #  0x0000000000000008 (RELASZ)             4896 (bytes)
    #  0x0000000000000009 (RELAENT)            24 (bytes)
    #  0x000000006ffffffe (VERNEED)            0x40b380
    #  0x000000006fffffff (VERNEEDNUM)         4
    #  0x000000006ffffff0 (VERSYM)             0x40add2
    #  0x0000000000000000 (NULL)               0x0
    #
    # We want the filenames in the '(NEEDED)' lines

    out = subprocess.check_output(('readelf', '--dynamic', '--wide', binary))

    regex = re.compile(r'\(NEEDED\).+\[(.+)\]')
    for line in out.splitlines():
        line = line.strip().decode('ascii')
        match = regex.search(line)
        if match:
            yield match.group(1)


def is_blacklisted(dependency, blacklist):
    name = os.path.basename(dependency)
    for pattern in blacklist:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def copy(dependency, destdir):
    destpath = os.path.join(destdir, os.path.basename(dependency))
    if not os.path.exists(destpath):
        print('Copying {} to {}'.format(dependency, destpath))
        shutil.copy(dependency, destpath)


class App:
    def __init__(self, blacklist, destdir, dry_run, dot_fp=None):
        self.path_for_binary = {}
        self.destdir = destdir
        self.dry_run = dry_run
        self.blacklist = blacklist
        self.processed_sonames = set()
        self.dot_fp = dot_fp

    def run(self, binary_path):
        if self.dot_fp:
            self.dot_fp.write('digraph {\n')
        binary = os.path.basename(binary_path)
        self.path_for_binary = list_soname_paths(binary_path)
        self.path_for_binary[binary] = binary_path
        self._traverse_tree(binary)
        if self.dot_fp:
            self.dot_fp.write('}\n')

    def _traverse_tree(self, binary):
        path = self.path_for_binary[binary]
        sonames = list_dependencies(path)
        for soname in sonames:
            if is_blacklisted(soname, self.blacklist):
                if self.dot_fp:
                    self._graph_blacklisted_dependency(binary, soname)
                continue

            if self.dot_fp:
                self._graph_dependency(binary, soname)

            if soname in self.processed_sonames:
                continue
            self.processed_sonames.add(soname)
            path = self.path_for_binary[soname]
            if not self.dry_run:
                copy(path, self.destdir)
            self._traverse_tree(soname)

    def _graph_blacklisted_dependency(self, binary, soname):
        self.dot_fp.write('  "{}" {};\n'.format(soname, DOT_BLACKLISTED_ATTRS))
        self.dot_fp.write('  "{}" -> "{}" {};\n'
                          .format(binary, soname, DOT_BLACKLISTED_ATTRS))

    def _graph_dependency(self, binary, soname):
        self.dot_fp.write('  "{}" -> "{}";\n'.format(binary, soname))


def main():
    parser = argparse.ArgumentParser()
    parser.description = DESCRIPTION

    parser.add_argument(
        '-d', '--destdir', metavar='DESTDIR',
        help='Copy to DESTDIR, defaults to the executable dir')

    parser.add_argument(
        '--exclude', metavar='FILE',
        help='Do not copy files whose name matches a line from FILE')

    parser.add_argument(
        '-n', '--dry-run', action='store_true', help='Simulate')

    parser.add_argument(
        '--dot', metavar='FILE',
        help='Create a graphviz graph of the dependencies in FILE')

    parser.add_argument('executable')

    args = parser.parse_args()

    blacklist = DEFAULT_BLACKLIST
    if args.exclude:
        if not os.path.isfile(args.exclude):
            parser.error('"{}" is not a file'.format(args.exclude))
        blacklist.extend(load_blacklist(args.exclude))

    if args.destdir and not os.path.isdir(args.destdir):
        parser.error('"{}" is not a directory'.format(args.destdir))

    if not os.path.isfile(args.executable):
        parser.error('"{}" is not a file'.format(args.executable))

    destdir = args.destdir or os.path.dirname(args.executable)

    # Reset the locale so that parsing output does not fail because of
    # translations
    os.environ['LANG'] = 'C'

    dot_fp = None
    if args.dot:
        try:
            dot_fp = open(args.dot, 'w')
        except IOError as exc:
            parser.error('Failed to write to "{}": {}'.format(args.dot, exc))

    app = App(blacklist=blacklist, destdir=destdir, dry_run=args.dry_run,
              dot_fp=dot_fp)
    try:
        app.run(args.executable)
    except IOError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    if dot_fp:
        dot_fp.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
# vi: ts=4 sw=4 et
