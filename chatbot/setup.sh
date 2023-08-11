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
docker build --tag "slurk/chatbot" -f chatbot/Dockerfile .
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
WAITING_ROOM=$(check_response scripts/create_default_waiting_room.sh ../slurk-bots/concierge/waiting_room_layout.json | jq .id)
echo "Waiting Room Id:"
echo $WAITING_ROOM

# create task room layout
TASK_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/chatbot/data/task_room_layout.json | jq .id)
echo "Task Room Layout Id:"
echo $TASK_ROOM_LAYOUT

# create dito task
TASK_ID=$(check_response scripts/create_task.sh  "Chatbot Task" 1 "$TASK_ROOM_LAYOUT" | jq .id)
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

# create bot
BOT_TOKEN=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/chatbot/data/bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "Task Bot Token: "
echo $BOT_TOKEN
BOT=$(check_response scripts/create_user.sh "Chatbot" "$BOT_TOKEN" | jq .id)
echo "Bot Id:"
echo $BOT
docker run -e SLURK_TOKEN=$BOT_TOKEN -e SLURK_USER=$BOT -e SLURK_WAITING_ROOM=$WAITING_ROOM -e TASK_ID=$TASK_ID -e SLURK_PORT=5000 --net="host" slurk/chatbot &
sleep 5

# create two users
USER1=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/chatbot/data/user_permissions.json 1 $TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
echo $USER1
USER2=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/chatbot/data/user_permissions.json 1 $TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
echo $USER2

cd ../slurk-bots/
