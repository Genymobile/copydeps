Contributions are welcome!

To submit a patch, check the following:

1. Make sure your Python code follows [PEP 8][PEP8].

You can check with the following command:

    flake8 --filename '*' --ignore E501 copydeps

(We ignore E501, line length because the code contains output of commands)

2. Make sure tests pass. You can run the test suite with:

    pytest

Then file a [pull request][PR] against the master branch.

[PEP8]: https://www.python.org/dev/peps/pep-0008/
[PR]: http://github.com/copydeps/pulls
