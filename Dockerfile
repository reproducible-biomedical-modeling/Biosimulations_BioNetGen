# Author: Ali Sinan Saglam
# Date: 3/30/2020
# Made for: BioNetGen docker image for BioSim

# FROM ubuntu:18.04
FROM continuumio/anaconda3

# update 
RUN apt-get update
# stuff we want
RUN apt-get install -y g++ vim perl cmake wget
# Get necessary libraries, SED-ML lib in particular
RUN pip install python-libsedml

# install bionetgen
WORKDIR /home/BNGDocker/
RUN git clone https://github.com/RuleWorld/bionetgen
WORKDIR /home/BNGDocker/bionetgen/
RUN git submodule init
RUN git submodule update 
WORKDIR /home/BNGDocker/bionetgen/bng2/
RUN make
WORKDIR /home/BNGDocker/simulation

# Copy over run script
COPY assets/run-bionetgen.py /usr/local/bin/run-bionetgen
RUN chmod ugo+x /usr/local/bin/run-bionetgen

# Temporary files for testing
COPY assets/test.bngl /home/BNGDocker/test.bngl
COPY assets/test.xml /home/BNGDocker/test.xml

# Entry point setup
ENTRYPOINT ["run-bionetgen"]
# if we need to setup some defaults 
# CMD []
