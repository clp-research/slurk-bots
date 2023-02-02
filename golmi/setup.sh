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

BOT_NAME="golmi"
NUMBER_USERS=2

GOLMI_HOST="127.0.0.1"
GOLMI_PORT=5001
GOLMI_SERVER="http://$GOLMI_HOST:$GOLMI_PORT"
GOLMI_PASSWORD="GiveMeTheBigBluePasswordOnTheLeft"

# run golmi
cd ../golmi
docker build --tag "golmi_server" -f dockerfile .
docker run --network host --restart unless-stopped -d -e GOLMI_HOST="127.0.0.1" -e GOLMI_PORT=5001 golmi_server
sleep 1

# build docker images for bots
cd ../slurk-bots
docker build --tag "slurk/$BOT_NAME-bot" -f $BOT_NAME/Dockerfile .
docker build --tag "slurk/concierge-bot" -f concierge/Dockerfile .

# run slurk
cd ../slurk
docker build --tag="slurk/server" -f Dockerfile .
export SLURK_DOCKER=slurk
scripts/start_server.sh
sleep 1

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
TASK_ROOM_LAYOUT=$(check_response scripts/create_layout.sh ../slurk-bots/$BOT_NAME/data/task_layout.json | jq .id)
echo "Task Room Layout Id:"
echo $TASK_ROOM_LAYOUT

# create math task
TASK_ID=$(check_response scripts/create_task.sh  "${BOT_NAME^} Task" $NUMBER_USERS "$TASK_ROOM_LAYOUT" | jq .id)
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
sleep 1

# create math bot
THIS_BOT_TOKEN=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/$BOT_NAME/data/bot_permissions.json | jq .id | sed 's/^"\(.*\)"$/\1/')
echo "$BOT_NAME Bot Token: "
echo $THIS_BOT_TOKEN
THIS_BOT=$(check_response scripts/create_user.sh "${BOT_NAME^}Bot" "$THIS_BOT_TOKEN" | jq .id)
echo "$BOT_NAME Bot Id:"
echo $THIS_BOT

# versions:
#  no_feedback: player can only send one message, does not know if the wizard selected the correct object
#  feedback: player can only send one message, is informed if the wizard selected the correct object
#  confirm_selection: player needs to confirm the wizard's selection
#  mouse_tracking: player can see the mouse movements of the wizard
docker run --net="host" \
    -e ${BOT_NAME^^}_TOKEN=$THIS_BOT_TOKEN \
    -e ${BOT_NAME^^}_USER=$THIS_BOT \
    -e ${BOT_NAME^^}_TASK_ID=$TASK_ID \
    -e SLURK_WAITING_ROOM=$WAITING_ROOM \
    -e SLURK_PORT=5000 \
    -e GOLMI_SERVER=$GOLMI_SERVER \
    -e GOLMI_PASSWORD=$GOLMI_PASSWORD \
    -e BOT_VERSION="confirm_selection" \
    slurk/$BOT_NAME-bot &
sleep 1

# create users
for ((c=0; c<NUMBER_USERS; c++))
do
    USER=$(check_response scripts/create_room_token.sh $WAITING_ROOM ../slurk-bots/$BOT_NAME/data/user_permissions.json 1 $TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
    echo "User $c Token: $USER"
done

cd ../slurk-bots
