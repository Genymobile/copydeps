Update CHANGELOG.md

Bump version number in copydeps.py and setup.cfg

Check/update README.md

Commit

Package and run tests

    tox --recreate --skip-missing-interpreters

Check the content of qpropgen.egg-info/PKG-INFO.

Tag

    git tag -a $version -m "Releasing $version"
    git push
    git push --tags

Upload

    twine upload .tox/dist/copydeps-$version.zip
