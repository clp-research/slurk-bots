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

check_response scripts/start_server_with_openvidu.sh
sleep 5

# create admin token
SLURK_TOKEN=$(check_response scripts/read_admin_token.sh)
echo "Admin Token:"
echo $SLURK_TOKEN

# create task room layout
TASK_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/audio_video_bot/task_room_layout.json | jq .id)
echo "Task Room Layout Id:"
echo $TASK_ROOM_LAYOUT

SESSION=$(check_response scripts/create_openvidu_session.sh)
SESSION_ID=$(echo $SESSION | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "Session Id:"
echo $SESSION_ID

# create demo task room
TASK_ROOM=$(check_response scripts/create_room.sh $TASK_ROOM_LAYOUT $SESSION_ID | jq .id)
echo "Task Room Id:"
echo $TASK_ROOM

# create two users
USER1=$(check_response scripts/create_room_token.sh $TASK_ROOM ../slurk-bots/audio_video_bot/user_permissions.json 1 | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "User Token:"
echo $USER1

USER2=$(check_response scripts/create_room_token.sh $TASK_ROOM ../slurk-bots/audio_video_bot/user_permissions.json 1 | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "User Token:"
echo $USER2

echo "Use the two tokens to log into slurk at localhost:5000, using either
private browsing sessions or two different browsers."
