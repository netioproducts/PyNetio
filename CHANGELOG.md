# Changelog
All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-08-13
Maintenance release: current Python versions, current devices, and inputs.

### Breaking
 - Python 3.11 or newer is required.
 - `OUTPUT.Energy_NR` and `OUTPUT.ReverseEnergy_NR` are now `EnergyNR` and
   `ReverseEnergyNR`. The old names never held a value.
 - A `Device` subclass now provides `init`, `get_info`, `get_outputs`,
   `get_inputs` and `_set_outputs`, and calls `super().__init__()`.

### Added
 - Reading inputs: `get_inputs`, `get_input`, `get_inputs_filtered` and
   `NumInputs`. Inputs are read only.
 - `INPUTS` command, also `DI`.
 - `Netio.__version__`.
 - Offline tests.

### Changed
 - Dropped the `pyopenssl` dependency.
 - Package metadata moved to the `[project]` table (PEP 621).
 - Publishing happens on a version tag, not on every push to master.
 - Updated demo device list, README and examples.

### Fixed
 - The CLI on current Python versions.
 - `INFO` command on firmware 5.x.
 - `EnergyNR` and `ReverseEnergyNR` were always empty.
 - The message for an invalid output number.
 - The example configuration file.

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
