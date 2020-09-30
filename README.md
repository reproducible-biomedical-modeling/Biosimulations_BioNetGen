# Biosimulators_BioNetGen
BioSimulators-compliant command-line interface and Docker image for the [BioNetGen](https://bionetgen.org/) simulation program.

## Contents
* [Installation](#installation)
* [Usage](#usage)
* [License](#license)
* [Development team](#development-team)
* [Questions and comments](#questions-and-comments)

## Installation

### Install Python package
```
pip install git+https://github.com/biosimulators/Biosimulators_BioNetGen
```

### Install Docker image
```
docker pull biosimulators/bionetgen
```

## Local usage
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

## Usage through Docker container
```
docker run \
  --tty \
  --rm \
  --mount type=bind,source="$(pwd)"/tests/fixtures,target=/root/in,readonly \
  --mount type=bind,source="$(pwd)"/tests/results,target=/root/out \
  biosimulators/bionetgen:latest \
    -i /root/in/BIOMD0000000297.omex \
    -o /root/out
```

## License
This package is released under the [MIT license](LICENSE).

## Development team
This package was developed by [Ali Sinan Saglam](https://scholar.google.com/citations?user=7TM0eekAAAAJ&hl=en) in the Faeder Lab at the University of Pittsburgh, the [Karr Lab](https://www.karrlab.org) at the Icahn School of Medicine at Mount Sinai, and the [Center for Reproducible Biomedical Modeling](http://reproduciblebiomodels.org).

## Questions and comments
Please contact [Ali Sinan Saglam](mailto:als251@pitt.edu) or the [BioSimulators Team](mailto:info@biosimulators.org) with any questions or comments.
