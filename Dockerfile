FROM --platform=amd64 mambaorg/micromamba:1.4-jammy

LABEL org.opencontainers.image.source https://github.com/ReubenJ/TORS-instance-converter

COPY ./environment.yml /tmp/env.yaml
RUN micromamba install -y -n base -f /tmp/env.yaml && \
    micromamba install mamba -y -n base -c conda-forge && \
    micromamba clean --all --yes

ENV PATH /opt/conda/bin:$PATH

COPY ./Shuntyard-Instance-Generator/environment.yml /tmp/env-generator.yml
RUN mamba env create -f /tmp/env-generator.yml && \
    mamba clean --all --yes

WORKDIR /TORS
COPY . .
RUN conda config --set channel_priority strict

USER root
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:apptainer/ppa && \
    apt-get update && \
    apt-get install -y apptainer && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# USER mambauser
