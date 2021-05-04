# BioSimulators-compliant Docker image for BioNetGen <https://bionetgen.org>
#
# Build image:
#   docker build \
#     --tag biosimulators/bionetgen:2.5.2 \
#     --tag biosimulators/bionetgen:latest \
#     .
#
# Run image:
#   docker run \
#     --tty \
#     --rm \
#     --mount type=bind,source="$(pwd)"/tests/fixtures,target=/root/in,readonly \
#     --mount type=bind,source="$(pwd)"/tests/results,target=/root/out \
#     biosimulators/bionetgen:latest \
#       -i /root/in/test.omex \
#       -o /root/out
#
# Author: Jonathan Karr <karr@mssm.edu>
# Author: Ali Sinan Saglam <als251@pitt.edu>
# Date: 2021-01-05

FROM python:3.9-slim-buster

ARG VERSION="0.1.8"
ARG SIMULATOR_VERSION=2.5.2

# metadata
LABEL \
    org.opencontainers.image.title="BioNetGen" \
    org.opencontainers.image.version="${SIMULATOR_VERSION}" \
    org.opencontainers.image.description="Open-source software package for rule-based modeling of complex biochemical systems" \
    org.opencontainers.image.url="https://bionetgen.org/" \
    org.opencontainers.image.documentation="https://bionetgen.org/" \
    org.opencontainers.image.source="https://github.com/biosimulators/Biosimulators_BioNetGen" \
    org.opencontainers.image.authors="BioSimulators Team <info@biosimulators.org>" \
    org.opencontainers.image.vendor="BioSimulators Team" \
    org.opencontainers.image.licenses="MIT" \
    \
    base_image="python:3.9-slim-buster" \
    version="${VERSION}" \
    software="BioNetGen" \
    software.version="${SIMULATOR_VERSION}" \
    about.summary="Open-source software package for rule-based modeling of complex biochemical systems" \
    about.home="https://bionetgen.org/" \
    about.documentation="https://bionetgen.org/" \
    about.license_file="https://github.com/RuleWorld/bionetgen/blob/master/LICENSE" \
    about.license="SPDX:MIT" \
    about.tags="rule-based modeling,kinetic modeling,dynamical simulation,systems biology,BNGL,SED-ML,COMBINE,OMEX,BioSimulators" \
    extra.identifiers.biotools="bionetgen" \
    maintainer="BioSimulators Team <info@biosimulators.org>"

# install BioNetGet and its dependencies
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
        perl \
        tar \
        wget \
    \
    && cd /tmp \
    && wget https://github.com/RuleWorld/bionetgen/releases/download/BioNetGen-${SIMULATOR_VERSION}/BioNetGen-${SIMULATOR_VERSION}-linux.tgz \
    && tar xvvf BioNetGen-${SIMULATOR_VERSION}-linux.tgz \
    && mv BioNetGen-${SIMULATOR_VERSION}/ /opt/ \
    \
    && rm BioNetGen-${SIMULATOR_VERSION}-linux.tgz \
    \
    && apt-get remove -y \
        wget \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
ENV PATH=${PATH}:/opt/BioNetGen-${SIMULATOR_VERSION}/

# install BioSimulators-compliant command-line interface to BioNetGen
COPY . /root/Biosimulators_BioNetGen
RUN pip install /root/Biosimulators_BioNetGen \
    && rm -rf /root/Biosimulators_BioNetGen
ENV VERBOSE=0 \
    MPLBACKEND=PDF

# setup entry point
ENTRYPOINT ["bionetgen"]
CMD []
