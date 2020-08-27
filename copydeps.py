#!/usr/bin/env python3
import argparse
import fnmatch
import os
import shutil
import subprocess
import sys

from elftools.elf.elffile import ELFFile


__appname__ = 'copydeps'
__version__ = '1.1.1'

DESCRIPTION = """\
Copy dependencies required by an executable to the specified dir. Dependencies
can be excluded. If a library is excluded then all its dependencies are
excluded unless a non-excluded library depend on them.

Can be used to inspect the dependencies of an executable through the generated
dependency graph.
"""

# Skip Linux dynamic loaders by default because they do not fit in the
# soname => path output of ldd
DEFAULT_EXCLUDE_LIST = ['ld-linux.so.*', 'ld-linux-x86-64.so.*']

DOT_EXCLUDED_ATTRS = '[color="gray" fontcolor="gray"]'


class MissingLibrariesError(Exception):
    def __init__(self, libs):
        self.libs = libs


def printerr(*args, **kwargs):
    kwargs['file'] = sys.stderr
    print(*args, **kwargs)


def load_exclude_list(filename):
    with open(filename, 'rt') as f:
        for line in f.readlines():
            line = line.strip()
            if not line or line[0] == '#':
                continue
            yield line


def list_soname_paths(executable):
    """Return a dict of the form soname => path for all the dependency of
    the executable"""
    out = subprocess.check_output(('ldd', executable))
    return parse_ldd_output(out)


def parse_ldd_output(ldd_output):
    """Return a dict of the form soname => path"""
    dct = {}
    missing_libs = []
    for line in ldd_output.splitlines():
        line = line.strip().decode('ascii')
        # line can be one of:
        # 1. linux-vdso.so.1 =>  (0x00007ffd6f3cd000)
        # 2. libcrypto.so.1.0.0 => /home/agateau/tmp/genymotion/./libcrypto.so.1.0.0 (0x00007f5ea40b6000)
        # 3. /lib64/ld-linux-x86-64.so.2 (0x0000562cf1094000)

        if not line:
            continue
        if '=>  (' in line:
            # Format #1, skip it
            continue
        if '=>' in line:
            # Format #2
            tokens = line.split(' ', 3)
            assert tokens[1] == '=>', 'Unexpected line format: {}'.format(line)

            soname = tokens[0]

            # Handle the case where a library has not been found
            if tokens[2:4] == ['not', 'found']:
                missing_libs.append(soname)

            path = tokens[2]
        else:
            # Format #3, set path to the soname
            soname = line.split(' ')[0]
            path = soname

        dct[soname] = path
    if missing_libs:
        raise MissingLibrariesError(missing_libs)
    return dct


def list_dependencies(binary):
    """Return the list of sonames this binary *directly* depends on"""
    with open(binary, 'rb') as f:
        elf = ELFFile(f)
        section = elf.get_section_by_name('.dynamic')
        if section is None:
            return
        for tag in section.iter_tags():
            if tag.entry.d_tag == 'DT_NEEDED':
                yield tag.needed


def is_excluded(dependency, exclude_list):
    name = os.path.basename(dependency)
    for pattern in exclude_list:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def copy(dependency, destdir):
    destpath = os.path.join(destdir, os.path.basename(dependency))
    if not os.path.exists(destpath):
        print('Copying {} to {}'.format(dependency, destpath))
        shutil.copy(dependency, destpath)


class App:
    def __init__(self, exclude_list, destdir, dry_run, dot_fp=None):
        self.path_for_binary = {}
        self.destdir = destdir
        self.dry_run = dry_run
        self.exclude_list = exclude_list
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
            if is_excluded(soname, self.exclude_list):
                if self.dot_fp:
                    self._graph_excluded_dependency(binary, soname)
                else:
                    printerr("Skipping {}".format(soname))
                continue

            if self.dot_fp:
                self._graph_dependency(binary, soname)

            if soname in self.processed_sonames:
                continue
            self.processed_sonames.add(soname)
            path = self.path_for_binary[soname]
            if self.dry_run:
                printerr("Would copy {} to {}".format(path, self.destdir))
            else:
                copy(path, self.destdir)
            self._traverse_tree(soname)

    def _graph_excluded_dependency(self, binary, soname):
        self.dot_fp.write('  "{}" {};\n'.format(soname, DOT_EXCLUDED_ATTRS))
        self.dot_fp.write('  "{}" -> "{}" {};\n'
                          .format(binary, soname, DOT_EXCLUDED_ATTRS))

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

    exclude_list = DEFAULT_EXCLUDE_LIST
    if args.exclude:
        if not os.path.isfile(args.exclude):
            parser.error('"{}" is not a file'.format(args.exclude))
        exclude_list.extend(load_exclude_list(args.exclude))

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

    exit_code = 0
    app = App(exclude_list=exclude_list, destdir=destdir, dry_run=args.dry_run,
              dot_fp=dot_fp)
    try:
        app.run(args.executable)
    except MissingLibrariesError as exc:
        printerr('Error, missing libraries:')
        for lib in exc.libs:
            printerr('- {}'.format(lib))
        exit_code = 1
    except IOError as exc:
        printerr(exc)
        exit_code = 1

    if dot_fp:
        dot_fp.close()

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
# vi: ts=4 sw=4 et
