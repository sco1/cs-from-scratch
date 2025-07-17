FROM ubuntu:jammy
ARG DEBIAN_FRONTEND=noninteractive

ARG PYTHON_PACKAGES="\
python3.12 python3.12-venv python3.12-tk \
python3.13 python3.13-venv python3.13-tk \
"

# Base utils
RUN apt-get update && apt-get install --no-install-recommends -yq software-properties-common gpg-agent
RUN apt-get -yq install git curl

# Python versions
RUN add-apt-repository ppa:deadsnakes/ppa && apt-get update
RUN apt-get install -yq --no-install-recommends ${PYTHON_PACKAGES}

# Shell
RUN apt-get -yq install zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

RUN chsh -s /usr/bin/zsh
ENV SHELL /usr/bin/zsh
ENTRYPOINT ["zsh"]
