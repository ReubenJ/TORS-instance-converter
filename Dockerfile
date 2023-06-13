FROM mambaorg/micromamba:1.4-jammy

COPY ./environment.yml /tmp/env.yaml
RUN micromamba install -y -n base -f /tmp/env.yaml && micromamba clean --all --yes
