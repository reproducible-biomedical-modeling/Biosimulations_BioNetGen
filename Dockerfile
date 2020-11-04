# BioSimulators-compliant Docker image for BioNetGen <https://bionetgen.org>
#
# Build image:
#   docker build \
#     --tag biosimulators/bionetgen:2.5.0 \
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
# Author: Ali Sinan Saglam <als251@pitt.edu>
# Author: Jonathan Karr <karr@mssm.edu>
# Date: 2020-04-13

FROM continuumio/miniconda3:4.8.2

ENV VERSION=2.5.1

# metadata
LABEL base_image="continuumio/miniconda3:4.8.2"
LABEL version="0.0.1"
LABEL software="BioNetGen"
LABEL software.version="${VERSION}"
LABEL about.summary="Open-source software package for rule-based modeling of complex biochemical systems"
LABEL about.home="https://bionetgen.org/"
LABEL about.documentation="https://bionetgen.org/"
LABEL about.license_file="https://github.com/RuleWorld/bionetgen/blob/master/LICENSE"
LABEL about.license="SPDX:MIT"
LABEL about.tags="rule-based modeling,kinetic modeling,dynamical simulation,systems biology,BNGL,SED-ML,COMBINE,OMEX,BioSimulators"
LABEL extra.identifiers.biotools="bionetgen"
LABEL maintainer="BioSimulators Team <info@biosimulators.org>"

# install requirements and BioNetGet
ENV CONDA_ENV=py37
RUN conda update -y -n base -c defaults conda \
    && conda create -y -n ${CONDA_ENV} python=3.7 \
    && conda install lxml
ENV PATH=/opt/conda/envs/${CONDA_ENV}/bin:${PATH}
RUN /bin/bash -c "source activate ${CONDA_ENV}"

RUN apt-get update -y \
    && apt-get install --no-install-recommends -y \
        cmake \
        g++ \
        git \
        make \
        perl \
        vim \
    \
    && git clone https://github.com/RuleWorld/bionetgen.git --branch BioNetGen-${VERSION} --depth 1 /root/bionetgen \
    && cd /root/bionetgen \
    && git submodule init \
    && git submodule update \
    && cd /root/bionetgen/bng2 \
    && make \
    \
    && apt-get remove -y \
        cmake \
        g++ \
        git \
        make \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
ENV PATH=${PATH}:/root/bionetgen/bng2

# install BioSimulators-compliant command-line interface to BioNetGen
COPY . /root/Biosimulators_BioNetGen
RUN pip install /root/Biosimulators_BioNetGen

# setup entry point
ENTRYPOINT ["bionetgen"]
CMD []
