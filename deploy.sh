#!/bin/bash

gcloud app deploy app.yaml worker.yaml

# delete versions not serving traffic
gcloud app versions list | grep 0.00 | awk '{print $2}' | xargs -l gcloud app versions delete 