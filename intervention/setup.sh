#!/usr/bin/env bash
set -eu

export SLURK_DOCKER=slurk
export FLASK_ENV=development

# build docker images for bots
cd ../slurk-bots
docker build --tag "slurk/audio-video-bot" -f audio_video_bot/Dockerfile .
docker build --tag "slurk/concierge-bot" -f concierge/Dockerfile .
docker build --tag "slurk/intervention-bot" -f intervention/Dockerfile .

# run slurk
cd ../slurk
docker build --tag="slurk/server" -f Dockerfile .
scripts/start_server.sh
sleep 5

SLURK_TOKEN=$(scripts/read_admin_token.sh)
echo $SLURK_TOKEN

WAITING_ROOM_LAYOUT_ID=$(scripts/create_layout.sh ../slurk-bots/concierge/waiting_room_layout.json | jq .id)
echo WAITING_ROOM_LAYOUT_ID=$WAITING_ROOM_LAYOUT_ID
WAITING_ROOM_ID=$(scripts/create_room.sh $WAITING_ROOM_LAYOUT_ID | jq .id)
echo WAITING_ROOM_ID=$WAITING_ROOM_ID

TASK_LAYOUT_ID=$(scripts/create_layout.sh ../slurk-bots/intervention/intervention_layout.json | jq .id)
TASK_ID=$(scripts/create_task.sh  "Intervention Task" 2 $TASK_LAYOUT_ID | jq .id)
echo TASK_ID
echo $TASK_ID

CONCIERGE_TOKEN=$(scripts/create_room_token.sh $WAITING_ROOM_ID ../slurk-bots/concierge/concierge_bot_permissions.json | jq -r .id)
CONCIERGE_USER=$(scripts/create_user.sh "ConciergeBot" $CONCIERGE_TOKEN | jq .id)

docker run -e SLURK_TOKEN=$CONCIERGE_TOKEN -e SLURK_USER=$CONCIERGE_USER -e SLURK_PORT=5000 --net="host" slurk/concierge-bot &

INT_TOKEN=$(scripts/create_room_token.sh $WAITING_ROOM_ID ../slurk-bots/intervention/intervention_bot_permissions.json | jq -r .id)
INT_USER=$(scripts/create_user.sh "InterventionBot" $INT_TOKEN | jq .id)

docker run -e SLURK_TOKEN=$INT_TOKEN -e SLURK_USER=$INT_USER -e SLURK_PORT=5000 -e TASK_ID=$TASK_ID --net="host" slurk/intervention-bot &

U1=$(scripts/create_room_token.sh $WAITING_ROOM_ID ../slurk-bots/intervention/user_permissions.json 1 $TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')
U2=$(scripts/create_room_token.sh $WAITING_ROOM_ID ../slurk-bots/intervention/user_permissions.json 1 $TASK_ID | jq .id | sed 's/^"\(.*\)"$/\1/')

echo USER TOKEN 1
echo $U1
echo USER TOKEN 2
echo $U2
