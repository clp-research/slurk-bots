# slurk audio pilot

[![Build Status](https://travis-ci.com/clp-research/slurk-audio-pilot.svg?branch=master)](https://travis-ci.com/clp-research/slurk-audio-pilot)

Pilot experiment on audio recording based on [slurk](https://github.com/clp-research/slurk).

## Instructions

### Use on MacOS

Following steps setup and run an OpenVidu Server and Slurk Audio Bot (+Slurk Server):

1. Open Terminal and run ```start-openvidu.sh```
2. Wait until the OpenVidu Server is running and displays "Access IP"
3. Open another Terminal and run ```start.sh```
4. Wait until the slurk server and audio bot are running (should return logs from audio bot stating a new session
on OpenVidu server was started like ```penvidu.Server - Created new session `pilot-4243a8e0-1054-11ea-87a6-025000000001```)
5. Open a browser with url [http://localhost:5000](http://localhost:5000)
6. Enter any username and the client token provided in the output of ```start.sh``` script
7. Rage because an error occurs
