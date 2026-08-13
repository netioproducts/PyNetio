# Changelog
All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-08-12
Big maintenance release. The package now works on current Python versions and
current devices.

### Fixed
 - The CLI with new versions of python.
 - `INFO` command for new device versions (5.x)
 - `EnergyNR` and `ReverseEnergyNR` fields
 - The message for an invalid output number.
 - The example configuration file.

### Changed
 - List of active demo devices in test suite
 - **Python 3.11 or newer is required.** Python 3.7 to 3.10 have all reached
   end of life.
 - Removed `pyopenssl` from dependencies.
 - Package metadata moved to the `[project]` table (PEP 621).
 - Update Readme and examples.

### Added
 - `Netio.__version__`.
 - Offline tests.

## [1.0.13] - 2023-09-21
### Fixed
 - name of the command line program

## [1.0.12] - 2023-09-21
### Added
 - all output parameters
 - NETIO demo devices in the test environment
 - switched the project to poetry

## [1.0.10] - 2023-06-22
### Fixed
 - error about a missing timeout property

## [1.0.9] - 2023-02-21
### Added
 - moved the project to pyproject.toml

## [1.0.8] - 2023-02-21
### Added
 - timeout parameter to JsonDevice

## [1.0.6] - 2021-04-07
### Added
 - fix argparse for python 3.6

## [1.0.3] - 2020-06-01
### Added
 - Major CLI redesign
 - Updated documentation

## [0.0.6] - 2020-05-16
### Fixed
 - off-by-one error in output indexing.

## [0.0.6] - 2020-05-12
### Added
 - support for self-signed certificates

## [0.0.5] - 2020-03-31
### Fixed
- Fix authentication error

### Added
- better communication handling

## [0.0.4] - 2020-03-30
### Fixed
- Pypi distribution package

## [0.0.3] - 2020-03-02
### Added
- Initial version
