#!/bin/bash
docker kill $(docker ps -q)
docker rm $(docker ps -a -q)
#build docker
cd ../slurk
docker build --tag="concierge-bot" -f sample_bots/concierge/Dockerfile ./
docker build --tag="slurk-server" ./ -f docker/slurk/Dockerfile
cd ../051_joint_reasoning
docker build --tag="cola-bot" ./
cd ../../AMT_aggreement_game

# Run Slurk
SLURK_SERVER_ID=$(docker run -p 80:5000 -e SECRET_KEY=your-key -v $PWD/images:/usr/src/slurk/app/static/images/ -e DEBUG=True -d slurk-server)
sleep 10
ADMIN_TOKEN=$(docker logs $SLURK_SERVER_ID 2> /dev/null | sed -n '/admin token:/{n;p;}')
echo $ADMIN_TOKEN

#Create Waitingroom 
WAITING_ROOM_LAYOUT=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d @waiting_room_layout.json \
       -s \
       localhost/api/v2/layout | jq .id)
sleep 1

curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "{\"name\": \"waiting_room\", \"label\": \"Waiting Room\", \"layout\": $WAITING_ROOM_LAYOUT}" \
       -s \
       localhost/api/v2/room
sleep 1

#Create Task
TASK_ROOM_LAYOUT=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d @cola_room_layout.json \
       -s \
       localhost/api/v2/layout | jq .id)

TASK_ID=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "{\"name\": \"cola\", \"num_users\": 2, \"layout\": $TASK_ROOM_LAYOUT}" \
       -s \
       localhost/api/v2/task | jq .id)
sleep 1

#Create Concierge Bot
CONCIERGE_BOT_TOKEN=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d '{"room": "waiting_room", "message_text": true, "room_create": true, "user_room_join": true, "user_room_leave": true}' \
       -s \
       localhost/api/v2/token | sed 's/^"\(.*\)"$/\1/')
sleep 1

docker run -e TOKEN=$CONCIERGE_BOT_TOKEN --net="host" concierge-bot &
sleep 5

#Create Cola Bot
COLA_BOT_TOKEN=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d '{"room": "waiting_room", "message_text": true, "user_room_join": true, "room_update": true, "token_invalidate": true, "user_query": true}' \
       -s \
       localhost/api/v2/token | sed 's/^"\(.*\)"$/\1/')
sleep 1

#docker run -e TOKEN=$COLA_BOT_TOKEN -e ECHO_TASK_ID=$TASK_ID --net="host" slurk/echo-bot &

docker run -e TOKEN=$COLA_BOT_TOKEN -e COLA_TASK_ID=$TASK_ID --net="host" cola-bot & 
sleep 10

#Create two user
curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "{\"room\": \"waiting_room\", \"message_text\": true, \"message_command\": true, \"task\": $TASK_ID}" \
       -s \
       localhost/api/v2/token | sed 's/^"\(.*\)"$/\1/'
sleep 1

curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "{\"room\": \"waiting_room\", \"message_text\": true, \"message_command\": true, \"task\": $TASK_ID}" \
       -s \
       localhost/api/v2/token | sed 's/^"\(.*\)"$/\1/'
sleep 1
