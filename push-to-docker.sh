#!/bin/bash

set -eux

function build_bot() {
    docker build -t slurk/$1-bot -f $1/Dockerfile .
    docker push slurk/$1-bot
}

build_bot minimal
build_bot echo
build_bot concierge
build_bot math
build_bot dito

