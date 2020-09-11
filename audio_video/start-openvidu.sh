#!/usr/bin/env bash

# define name
OPENVIDU_CONTAINER="openvidu-recording-server"
OPENVIDU_SECRET="y3kQwl0qvaWiN7w69WjJGjMKk1b0E7QK01ztKeL1IPY"
RECORD_DIR="C:/docker/"

# kill existing containers
#docker kill "${OPENVIDU_CONTAINER}" >> /dev/null

# start openvidu server for recording audio
docker run -p 4443:4443 --rm \
    -v //var/run/docker.sock:/var/run/docker.sock \
    -e openvidu.secret=$OPENVIDU_SECRET \
    -e openvidu.publicurl=https://localhost:4443 \
    -v $RECORD_DIR:/home/expA/recordings \
    -e openvidu.recording=true \
    -e openvidu.recording.path=/home/expA/recordings \
    --name=$OPENVIDU_CONTAINER \
    openvidu/openvidu-server-kms:2.11.0