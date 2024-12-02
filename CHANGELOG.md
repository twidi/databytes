# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3] - 2024-12-02

### Added

- Ability to fill a struct from a dictionary (`fill_from_dict` method)
- Ability to fill a struct from another one (`fill_from` method)
- Ability to extract data from a struct as a dictionary (`to_dict` method)
- Ability to clear the buffer a struct points to (`clear_buffer` method)

## [1.2.1] - 2024-11-30

### Changed

- Sub-structs endianness is now inherited from parent struct

## [1.2] - 2024-11-29

### Added
- Ability to set the endianness of a struct

## [1.1] - 2024-11-29

### Changed
- New `attach_buffer` method to attach new buffer with possible new offset (`set_new_buffer` is still present, not taking offset, kept for backward compatibility)
- Internal methods are now prefixed with `_` to better indicate private methods

## [1.0] - 2024-11-29

First official release of the `databytes` package, providing a Python library to manipulate bytes with a clean API.
