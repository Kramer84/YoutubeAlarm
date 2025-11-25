#!/bin/bash

# Name of the conda environment
ENV_NAME="youtubeAlarm"

# Create the conda environment and install all the necessary packages in one step
conda create --name $ENV_NAME python=3.8 \
              conda-forge::yt-dlp \
              conda-forge::requests \
              conda-forge::ffmpeg \
              conda-forge::psutil \
              conda-forge::aioconsole \
              conda-forge::mutagen -y

# Activate the environment
source activate $ENV_NAME

# Install additional libraries via pip if necessary
pip install python-vlc

# Deactivate the environment
conda deactivate

echo "Conda environment '$ENV_NAME' created and required libraries installed."
