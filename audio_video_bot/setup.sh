#!/usr/bin/env bash
set -eu

# export SLURK_OPENVIDU_URL and SLURK_OPENVIDU_SECRET before starting the script

function errcho {
    echo "$@" 1>&2
}

function check_response {
    response=$("$@")
    if [ -z "$response" ]; then
        errcho "Unexpected error for call to: $1"
        exit 1
    fi
    echo "$response"
}

export SLURK_DOCKER=slurk
export FLASK_ENV=development

# build docker images for bots
cd ../slurk-bots
docker build --tag "slurk/audio-video-bot" -f audio_video_bot/Dockerfile .
docker build --tag "slurk/concierge-bot" -f concierge/Dockerfile .

# run slurk
cd ../slurk
docker build --tag="slurk/server" -f Dockerfile .
check_response scripts/start_server_with_openvidu.sh
sleep 5

# create admin token
SLURK_TOKEN=$(check_response scripts/read_admin_token.sh)
echo "Admin Token:"
echo $SLURK_TOKEN

# create waiting room + layout
WAITING_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/concierge/waiting_room_layout.json | jq .id)
echo "Waiting Room Layout Id:"
echo $WAITING_ROOM_LAYOUT
WAITING_ROOM=$(check_response scripts/create_room.sh $WAITING_ROOM_LAYOUT | jq .id)
echo "Waiting Room Id:"
echo $WAITING_ROOM

# create task room layout
TASK_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/audio_video_bot/task_room_layout.json | jq .id)
echo "Task Room Layout Id:"
echo $TASK_ROOM_LAYOUT

# create av task
AV_TASK_ID=$(check_response scripts/create_task.sh  "Audio Video Task" 2 "$TASK_ROOM_LAYOUT" | jq .id)
echo "Task Id:"
echo $AV_TASK_ID

# create concierge bot
CONCIERGE_BOT_TOKEN=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/concierge/concierge_bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "Concierge Bot Token:"
echo $CONCIERGE_BOT_TOKEN
CONCIERGE_BOT=$(check_response scripts/create_user.sh "ConciergeBot" $CONCIERGE_BOT_TOKEN | jq .id)
echo "Concierge Bot Id:"
echo $CONCIERGE_BOT
docker run -e SLURK_TOKEN="$CONCIERGE_BOT_TOKEN" -e SLURK_USER=$CONCIERGE_BOT -e SLURK_PORT=5000 -e SLURK_OPENVIDU_URL=$SLURK_OPENVIDU_URL --net="host" slurk/concierge-bot &
sleep 5

# create av bot
AV_BOT_TOKEN=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/audio_video_bot/bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "Audio Video Bot Token: "
echo $AV_BOT_TOKEN
AV_BOT=$(check_response scripts/create_user.sh "AudioVideoBot" "$AV_BOT_TOKEN" | jq .id)
echo "Audio Video Bot Id:"
echo $AV_BOT
docker run -e SLURK_TOKEN=$AV_BOT_TOKEN -e SLURK_USER=$AV_BOT -e AV_TASK_ID=$AV_TASK_ID -e SLURK_PORT=5000 --net="host" slurk/audio-video-bot &
sleep 5

# create a user
USER1=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/audio_video_bot/user_permissions.json 1 $AV_TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "User Token:"
echo $USER1

# create a user
USER2=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/audio_video_bot/user_permissions.json 1 $AV_TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "User Token:"
echo $USER2
