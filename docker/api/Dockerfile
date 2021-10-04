FROM python:3.8

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
COPY requirements.txt /home/kernelci/
RUN pip install --requirement requirements.txt

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--reload"]
