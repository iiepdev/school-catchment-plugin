# EdPlanning
![tests](https://github.com/GispoCoding/edplanning/workflows/Tests/badge.svg)
[![codecov.io](https://codecov.io/github/GispoCoding/edplanning/coverage.svg?branch=master)](https://codecov.io/github/GispoCoding/edplanning?branch=master)
![release](https://github.com/GispoCoding/edplanning/workflows/Release/badge.svg)
[![GPLv3 license](https://img.shields.io/badge/License-GPLv3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

QGIS plugin for analysing school locations based on Openstreetmap data.

Currently, the plugin calculates catchment areas (isochrones) to a specified layer of schools with a selected mode of transport (foot, hike, bike, car) and a selected distance in meters or minutes (e.g. 1 kilometer, or 30 minutes of transit).

The plugin employs the [Graphhopper routing backend](https://github.com/graphhopper/graphhopper). Therefore, you must have a Graphhopper instance running, or you may use any commercial Graphhopper service. We assume your Graphhopper config contains at least the following routing profiles:

```
  profiles:
    - name: foot
      vehicle: foot
      weighting: fastest
    - name: hike
      vehicle: hike
      weighting: shortest
    - name: bike
      vehicle: bike
      weighting: fastest
    - name: car
      vehicle: car
      weighting: fastest
```

### Development

Refer to [development](docs/development.md) for developing this QGIS3 plugin.

## License
This plugin is licenced with
[GNU General Public License, version 3](https://www.gnu.org/licenses/gpl-3.0.html).
See [LICENSE](LICENSE) for more information.
