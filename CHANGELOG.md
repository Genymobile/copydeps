# Changelog

## 1.1.1 - 2020.08.27

- Exit with 1 if copydeps fails to copy a library
- Do not use the "blacklist" term in the code, doc or filenames
- Improve --dry-run output: print the name of included and excluded libraries
- Setup continuous integration using GitHub actions

## 1.1.0 - 2019.02.13

- Use pyelftools instead of parsing `readelf` output
- Added tests for `ldd` output parser
- Improved report of missing libraries
- Do not fail on local shared objects (#7)

## 1.0.0 - 2017.06.27

- First release
