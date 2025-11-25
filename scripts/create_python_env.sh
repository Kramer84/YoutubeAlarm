#!/bin/bash

# Name of the conda environment
ENV_NAME="youtubeAlarm"

# Create the conda environment and install all the necessary packages in one step
conda create --name $ENV_NAME python=3.10 \
    conda-forge::ffmpeg \
    conda-forge::nodejs \
    conda-forge::psutil \
    conda-forge::aioconsole \
    conda-forge::mutagen \
    conda-forge::requests -y

# Activate the environment
conda activate $ENV_NAME

# Install additional libraries via pip if necessary
pip install python-vlc
pip install -U yt-dlp  # -U ensures you get the latest version

# Deactivate the environment
conda deactivate

echo "Conda environment '$ENV_NAME' created and required libraries installed."
