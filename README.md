# copydeps

## Introduction

copydeps is a tool to analyze and copy the dependencies of a Linux binary. It
is useful to create light, self-contained installers.

It works on both executables and libraries.

## Requirements

Python 3

## Installation

Put `copydeps` somewhere in your PATH, or just run it by using the full path to
it.

## Usage

### Copying dependencies

Assuming you want to copy all dependencies of the `foo` binary to the current
directory, run:

    copydeps /path/to/foo -d .

The list probably includes way too many libraries you can assume to be
installed on the destination system. To tell copydeps to ignore them, create a
blacklist file (you can have a look at `blacklist.sample` for inspiration) and
run it like this:

    copydeps --exclude your/blacklist /path/to/foo -d .

### Analyzing dependencies

You can tell copydeps to generate a dependency diagram using the `--dot`
option.  If you just want to look at the dependency diagram, add the
`--dry-run` option to prevent copying:

    copydeps --exclude your/blacklist /path/to/foo --dry-run --dot foo.dot

You can now view the diagram using any Graphviz viewer, such as [xdot][]

As an example, here is the dependency diagram of Qt5QuickControls2:

[![Qt5QuickControls2 dependencies](screenshot/screenshot-small.png)](screenshot/screenshot.png)

[xdot]: https://github.com/jrfonseca/xdot.py

## Limitations

copydeps does not detect libraries loaded with `dlopen()`.
