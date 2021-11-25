# CHANGELOG

## [0.3.0] - 2021-11-25

### Added

- Option to merge isochrones by field value, e.g. merging isochrones of multiple entrances of the same building

### Changed

- Isochrone original_fid field is now string (due to possible merging of isochrones)
- UI checkboxes moved to separate Extra options field to indicate they are optional

## [0.2.1] - 2021-11-24

### Changed

- Fixes to release workflow

## [0.2.0] - 2021-11-24

### Added

- Option to limit areas to polygon boundaries, i.e. limiting isochrones to given polygons around each point

### Changed

- Updated test and development dependencies
- Isochrones are now multipolygons (due to boundary intersections) instead of simple polygons

## [0.1.0] - 2021-06-11

- First official version published
