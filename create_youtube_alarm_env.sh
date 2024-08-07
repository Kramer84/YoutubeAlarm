#!/bin/bash

# Name of the conda environment
ENV_NAME="youtubeAlarm"

# Create the conda environment with Python 3.8
conda create --name $ENV_NAME python=3.8 -y

# Activate the environment
source activate $ENV_NAME

# Install the required libraries
conda install -c conda-forge yt-dlp requests ffmpeg psutil -y

# Deactivate the environment
conda deactivate

echo "Conda environment '$ENV_NAME' created and required libraries installed."
