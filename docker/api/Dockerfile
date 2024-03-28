# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021-2024 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

FROM python:3.11
MAINTAINER "KernelCI TSC" <kernelci-tsc@groups.io>

RUN apt-get update && apt-get install --no-install-recommends -y git

# Upgrade pip3 - never mind the warning about running this as root
RUN pip3 install --upgrade pip

# Create kernelci user
RUN useradd kernelci -u 1000 -d /home/kernelci -s /bin/bash
RUN mkdir -p /home/kernelci
RUN chown kernelci: /home/kernelci
USER kernelci
ENV PATH=$PATH:/home/kernelci/.local/bin
WORKDIR /home/kernelci

# Install requirements
COPY requirements*.txt /home/kernelci/
ARG REQUIREMENTS=requirements.txt
RUN pip install --requirement ${REQUIREMENTS}

# Install kernelci Python package from kernelci-core
USER root
ARG core_url=https://github.com/kernelci/kernelci-core.git
ARG core_rev=main
RUN git clone --depth=1 $core_url /tmp/kernelci-core
WORKDIR /tmp/kernelci-core
RUN git fetch origin $core_rev
RUN git checkout FETCH_HEAD
RUN python3 -m pip install .
RUN cp -R config /etc/kernelci/
WORKDIR /home/kernelci
RUN rm -rf /tmp/kernelci-core
USER kernelci

CMD ["uvicorn", "api.main:versioned_app", "--host", "0.0.0.0", "--reload"]
