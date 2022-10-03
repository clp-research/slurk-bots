#!/usr/bin/env bash
set -eu

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

# build docker images for bots
cd ../slurk-bots
docker build --tag "slurk/ccbts-bot" -f ccbts/Dockerfile .
docker build --tag "slurk/concierge-bot" -f concierge/Dockerfile .

# run slurk
cd ../slurk
docker build --tag="slurk/server" -f Dockerfile .
export SLURK_DOCKER=slurk
scripts/start_server.sh
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
TASK_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/ccbts/ccbts_task_layout.json | jq .id)
echo "Task Room Layout Id:"
echo $TASK_ROOM_LAYOUT

# create math task
TASK_ID=$(check_response scripts/create_task.sh  "Ccbts Task" 2 "$TASK_ROOM_LAYOUT" | jq .id)
echo "Task Id:"
echo $TASK_ID

# create concierge bot
CONCIERGE_BOT_TOKEN=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/concierge/concierge_bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "Concierge Bot Token:"
echo $CONCIERGE_BOT_TOKEN
CONCIERGE_BOT=$(check_response scripts/create_user.sh "ConciergeBot" $CONCIERGE_BOT_TOKEN | jq .id)
echo "Concierge Bot Id:"
echo $CONCIERGE_BOT
docker run -e SLURK_TOKEN="$CONCIERGE_BOT_TOKEN" -e SLURK_USER=$CONCIERGE_BOT -e SLURK_PORT=5000 --net="host" slurk/concierge-bot &
sleep 5

# create math bot
CCBTS_BOT_TOKEN=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/ccbts/ccbts_bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "ccbts Bot Token: "
echo $CCBTS_BOT_TOKEN
CCBTS_BOT=$(check_response scripts/create_user.sh "CcbtsBot" "$CCBTS_BOT_TOKEN" | jq .id)
echo "Ccbts Bot Id:"
echo $CCBTS_BOT
docker run -e CCBTS_TOKEN=$CCBTS_BOT_TOKEN -e CCBTS_USER=$CCBTS_BOT -e CCBTS_TASK_ID=$TASK_ID -e SLURK_WAITING_ROOM=$WAITING_ROOM -e SLURK_PORT=5000 --net="host" slurk/ccbts-bot &
sleep 5

# create users
USER1=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/ccbts/ccbts_user_permissions.json 1 $TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "User 1 Token:"
echo $USER1

USER1=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/ccbts/ccbts_user_permissions.json 1 $TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "User 2 Token:"
echo $USER1

cd ../slurk-bots
