#!/usr/bin/env bash
set -eu

export SLURK_DOCKER=slurk
export FLASK_ENV=development

# build docker images for bots
cd ../slurk-bots
docker build --tag "slurk/taboo-bot" -f taboo/Dockerfile .

# run slurk
cd ../slurk
docker build --tag="slurk/server" -f Dockerfile .
scripts/start_server.sh
sleep 5

SLURK_TOKEN=$(scripts/read_admin_token.sh)
echo $SLURK_TOKEN

TASK_LAYOUT_ID=$(scripts/create_layout.sh ../slurk-bots/taboo/taboo_layout.json | jq .id)
TABOO_ROOM_ID=$(scripts/create_room.sh $TASK_LAYOUT_ID | jq .id)
echo TASK_LAYOUT_ID
echo $TASK_LAYOUT_ID
echo TABOO_ROOM_ID
echo $TABOO_ROOM_ID

TABOO_TOKEN=$(scripts/create_room_token.sh $TABOO_ROOM_ID ../slurk-bots/taboo/taboo_bot_permissions.json | jq -r .id)
TABOO_USER=$(scripts/create_user.sh "TabooBot" $TABOO_TOKEN | jq .id)
echo TABOO_TOKEN
echo $TABOO_TOKEN
echo TABOO_USER
echo $TABOO_USER

TABOO_DATA="food.json"

docker run -e SLURK_TOKEN=$TABOO_TOKEN -e SLURK_USER=$TABOO_USER -e TABOO_DATA=$TABOO_DATA -e SLURK_PORT=5000 --net="host" slurk/taboo-bot &

U1=$(scripts/create_room_token.sh $TABOO_ROOM_ID ../slurk-bots/taboo/user_permissions.json 2 | jq .id | sed 's/^"\(.*\)"$/\1/')
U2=$(scripts/create_room_token.sh $TABOO_ROOM_ID ../slurk-bots/taboo/user_permissions.json 2 | jq .id | sed 's/^"\(.*\)"$/\1/')

echo USER TOKEN 1
echo $U1
echo USER TOKEN 2
echo $U2