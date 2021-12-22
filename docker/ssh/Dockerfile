# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

FROM debian:bullseye-slim
MAINTAINER "KernelCI TSC" <kernelci-tsc@groups.io>

# Install openssh-server
RUN apt update && apt install  openssh-server -y

# Create privilege separation directory
RUN mkdir -p /run/sshd

# Create kernelci user
RUN useradd kernelci -u 1000 -d /home/kernelci -s /bin/bash
RUN mkdir -p /home/kernelci
RUN chown kernelci: /home/kernelci

# SSH server will run on PORT 22
EXPOSE 22

# Copy sshd_config file
COPY sshd_config /etc/ssh/

# Run SSH server in detached mode
CMD ["/usr/sbin/sshd","-D"]
