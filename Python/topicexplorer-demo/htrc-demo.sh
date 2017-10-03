#!/bin/bash

DATA_HOME=$HOME/HTRC/demo/htrc-data
SECURE_VOLUME=/media/secure_volume

if [ ! -d "$SECURE_VOLUME" ]; then
  # Control will enter here if $DIRECTORY doesn't exist.
  echo "Please enter Secure Mode before accessing Data API."
  exit 1
fi

# Activate the htrc-demo Python 2.7 environment
# this is not necessary anymore since topicexplorer has moved to Python 3.5
# source activate htrc-demo

echo "Downloading texts from HTRC Data API..."
htrc download -o $SECURE_VOLUME/volumes htrc-id

echo "Running topic modeling algorithms..."
topicexplorer init $SECURE_VOLUME/volumes --htrc --name "HTRC Demo Corpus"
topicexplorer train $SECURE_VOLUME/volumes.ini --iter 50 -k 5 10 20 40 80 --context-type book

echo "Getting metadata..."
htrc metadata $SECURE_VOLUME/volumes/ > $SECURE_VOLUME/volumes/metadata.json

echo "Launching topic explorer..."
topicexplorer launch $SECURE_VOLUME/volumes.ini

# Deactivate the htrc-demo environment
# source deactivate
