# Author: Ali Sinan Saglam
# Date: 3/30/2020
# Made for: BioNetGen docker image for BioSim

# FROM ubuntu:18.04
FROM continuumio/anaconda3

# WORKDIR /home/BNGBuild
# stuff for python3 compilation
# RUN apt-get install -y build-essential python-dev python-setuptools python-pip python-smbus
# RUN apt-get install -y libncursesw5-dev libgdbm-dev libc6-dev
# RUN apt-get install -y zlib1g-dev libsqlite3-dev git 
# RUN apt-get install -y libssl-dev openssl libffi-dev libxml2-dev libxslt1-dev liblzma-dev
# # Get Python source code
# RUN wget https://www.python.org/ftp/python/3.6.7/Python-3.6.7rc1.tgz
# # Build python with --enable-shared flag
# RUN tar xvf Python-3.6.7rc1.tgz
# WORKDIR /home/BNGBuild/Python-3.6.7rc1
# RUN mkdir /home/BNGBuild/python3
# ENV LD_LIBRARY_PATH /home/BNGBuild/Python-3.6.7rc1
# RUN ./configure --enable-shared --prefix=/home/BNGBuild/python3
# RUN make; make install
# # set the system python3 to the one we just compiled
# ENV PATH /home/BNGBuild/python3/bin:$PATH
# # Update pip and install a couple dependencies for later on
# RUN pip3 install --upgrade pip
# # staticx for static binary making and dependencies
# RUN pip3 install backports.lzma patchelf-wrapper staticx 

# update 
RUN apt-get update
# stuff we want
RUN apt-get install -y g++ vim perl cmake wget
# install bionetgen
WORKDIR /home/apps/
RUN git clone https://github.com/RuleWorld/bionetgen
WORKDIR /home/apps/bionetgen/bng2/
# Copy over run script
COPY assets/run-bionetgen.py /usr/local/bin/run-bionetgen
RUN chmod ugo+x /usr/local/bin/run-bionetgen

# Entry point setup
ENTRYPOINT ["run-bionetgen"]
# if we need to setup some defaults 
# CMD []
