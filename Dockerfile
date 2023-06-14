FROM mambaorg/micromamba:1.4-jammy

LABEL org.opencontainers.image.source https://github.com/ReubenJ/TORS-instance-converter

COPY ./environment.yml /tmp/env.yaml
RUN micromamba install -y -n base -f /tmp/env.yaml && micromamba clean --all --yes
ENV PATH /opt/conda/bin:$PATH

WORKDIR /TORS
COPY . .
RUN conda config --set channel_priority strict && \
    snakemake --cores all --use-conda --conda-create-envs-only
