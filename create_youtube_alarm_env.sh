#!/bin/bash

# Name of the conda environment
ENV_NAME="youtubeAlarm"

# Create the conda environment with the latest version of Python
conda create --name $ENV_NAME python -y

# Activate the environment
source activate $ENV_NAME

# Install the required libraries from conda
conda install -c conda-forge yt-dlp requests ffmpeg psutil aioconsole -y
conda install -c anaconda logging argparse -y
conda install -c conda-forge mutagen slugify -y

# Install additional libraries via pip if necessary
pip install python-vlc

# Deactivate the environment
conda deactivate

echo "Conda environment '$ENV_NAME' created and required libraries installed."
