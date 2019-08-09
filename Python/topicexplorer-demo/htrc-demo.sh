#!/bin/bash

DATA_HOME=$HOME/HTRC/htrc-id
SECURE_VOLUME=/media/secure_volume

if [ ! -d "$SECURE_VOLUME" ]; then
  # Control will enter here if $DIRECTORY doesn't exist.
  echo "Installing topic explorer and htrc library, if not already installed"
  pip install htrc
  pip install topicexplorer
  echo "Please enter Secure Mode before accessing Data API."
  exit 1
fi

echo "Downloading texts from HTRC Data API..."
htrc download -o $SECURE_VOLUME/volumes $DATA_HOME

echo "Running topic modeling algorithms..."
topicexplorer init --htrc --name "HTRC Demo Corpus" $SECURE_VOLUME/volumes/ $SECURE_VOLUME/volumes.ini
topicexplorer train $SECURE_VOLUME/volumes.ini --iter 50 -k 5 10 20 40 80 --context-type book

echo "Launching topic explorer..."
topicexplorer launch $SECURE_VOLUME/volumes.ini
