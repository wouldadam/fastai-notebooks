FROM "nvcr.io/nvidia/pytorch:23.06-py3"

ARG USER_NAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

ENV FASTAI_HOME=/workspaces/fastai/.fastai
ENV TORCH_HOME=/workspaces/fastai/.torch
ENV PRE_COMMIT_HOME=/workspaces/fastai/.precommit

# Install python libs
RUN pip install fastai nbdev fastbook ipywidgets
RUN pip install black flake8 pre-commit

# Create a non-root user with sudo
RUN groupadd --gid $USER_GID $USER_NAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USER_NAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USER_NAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USER_NAME \
    && chmod 0440 /etc/sudoers.d/$USER_NAME

# Mess with juptyer permissions and install yarn otherwise the extension manager cli is unhappy
SHELL [ "/bin/bash", "--login", "-c" ]
RUN chown -R $USER_GID:$USER_GID /usr/local/share/jupyter \
    && source /usr/local/nvm/nvm.sh \
    && npm install -g yarn

# Switch to our user
USER $USER_NAME

# Install jupyter extensions
RUN source /usr/local/nvm/nvm.sh \
    && jupyter-labextension install @jupyter-widgets/jupyterlab-manager