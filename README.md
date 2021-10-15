[![Latest release](https://img.shields.io/github/v/tag/biosimulators/Biosimulators_BioNetGen)](https://github.com/biosimulations/Biosimulators_BioNetGen/releases)
[![PyPI](https://img.shields.io/pypi/v/biosimulators_bionetgen)](https://pypi.org/project/biosimulators_bionetgen/)
[![CI status](https://github.com/biosimulators/Biosimulators_BioNetGen/workflows/Continuous%20integration/badge.svg)](https://github.com/biosimulators/Biosimulators_BioNetGen/actions?query=workflow%3A%22Continuous+integration%22)
[![Test coverage](https://codecov.io/gh/biosimulators/Biosimulators_BioNetGen/branch/dev/graph/badge.svg)](https://codecov.io/gh/biosimulators/Biosimulators_BioNetGen)
[![All Contributors](https://img.shields.io/github/all-contributors/biosimulators/Biosimulators_BioNetGen/HEAD)](#contributors-)

# BioSimulators-BioNetGen
BioSimulators-compliant command-line interface and Docker image for the [BioNetGen](https://bionetgen.org/) simulation program.

This command-line interface and Docker image enable users to use BioNetGen to execute [COMBINE/OMEX archives](https://combinearchive.org/) that describe one or more simulation experiments (in [SED-ML format](https://sed-ml.org)) of one or more models (in [BNGL format](https://bionetgen.org])).

A list of the algorithms and algorithm parameters supported by BioNetGen is available at [BioSimulators](https://biosimulators.org/simulators/bionetgen).

A simple web application and web service for using BioNetGen to execute COMBINE/OMEX archives is also available at [runBioSimulations](https://run.biosimulations.org).

## Installation

### Install Python package

After installing BioNetGen, use pip to install this package as illustrated below.
```
pip install biosimulators-bionetgen
```

### Install Docker image
```
docker pull ghcr.io/biosimulators/bionetgen
```

## Usage

### Local usage
```
usage: bionetgen [-h] [-d] [-q] -i ARCHIVE [-o OUT_DIR] [-v]

BioSimulators-compliant command-line interface to the BioNetGen simulation program <https://bionetgen.org>.

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           full application debug mode
  -q, --quiet           suppress all console output
  -i ARCHIVE, --archive ARCHIVE
                        Path to OMEX file which contains one or more SED-ML-
                        encoded simulation experiments
  -o OUT_DIR, --out-dir OUT_DIR
                        Directory to save outputs
  -v, --version         show program's version number and exit
```

### Usage through Docker container
The entrypoint to the Docker image supports the same command-line interface described above.

For example, the following command could be used to use the Docker image to execute the COMBINE/OMEX archive `./modeling-study.omex` and save its outputs to `./`.

```
docker run \
  --tty \
  --rm \
  --mount type=bind,source="$(pwd)",target=/root/in,readonly \
  --mount type=bind,source="$(pwd)",target=/root/out \
  ghcr.io/biosimulators/bionetgen:latest \
    -i /root/in/modeling-study.omex \
    -o /root/out
```

## Documentation
Documentation is available at https://docs.biosimulators.org/Biosimulators_BioNetGen/.

## License
This package is released under the [MIT license](LICENSE).

## Development team
This package was developed by the [Karr Lab](https://www.karrlab.org) at the Icahn School of Medicine at Mount Sinai, [Ali Sinan Saglam](https://scholar.google.com/citations?user=7TM0eekAAAAJ&hl=en) in the Faeder Lab at the University of Pittsburgh, and the [Center for Reproducible Biomedical Modeling](http://reproduciblebiomodels.org) with assistance from the contributors listed [here](CONTRIBUTORS.md).

## Questions and comments
Please contact the [BioSimulators Team](mailto:info@biosimulators.org) with any questions or comments about the command-line program or Docker image. Please contact [Ali Sinan Saglam](mailto:als251@pitt.edu) with any questions or comments about BioNetGen.
