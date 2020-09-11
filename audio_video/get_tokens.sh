# Upload layouts
WAITING_ROOM_LAYOUT=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "@layouts/waiting_room.json" \
       $HOST:$PORT/api/v2/layout | jq .id)

PILOT_ROOM_LAYOUT=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "@layouts/pilot.json" \
       $HOST:$PORT/api/v2/layout | jq .id)


# Create waiting room
WAITING_ROOM=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "{\"name\": \"waiting_room\", \"label\": \"Waiting Room\", \"layout\": $WAITING_ROOM_LAYOUT}" \
       $HOST:$PORT/api/v2/room | jq .name)


# Create task
TASK_ID=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "{\"name\": \"pilot\", \"num_users\": 1, \"layout\": $PILOT_ROOM_LAYOUT }" \
       $HOST:$PORT/api/v2/task | jq .id)

# start bots
CONCIERGE_BOT_TOKEN=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "{\"room\": $WAITING_ROOM, \"message_text\": true, \"room_create\": true, \"user_room_join\": true, \"user_room_leave\": true}" \
       $HOST:$PORT/api/v2/token | sed 's/^"\(.*\)"$/\1/')
docker run --name concierge-bot --net="host" -d slurk/concierge-bot -t "$CONCIERGE_BOT_TOKEN" -c $HOST -p $PORT

AUDIO_BOT_TOKEN=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "{\"room\": $WAITING_ROOM, \"message_text\": true, \"message_command\": true, \"user_room_join\": true}" \
       $HOST:$PORT/api/v2/token | sed 's/^"\(.*\)"$/\1/')
docker run --name audio-bot --net="host" -d slurk/audio-bot -t "$AUDIO_BOT_TOKEN" -c $HOST -p $PORT --task-id $TASK_ID --openvidu-url "$OPENVIDU_URL" --openvidu-secret "$OPENVIDU_SECRET" --openvidu-verify "$OPENVIDU_VERIFY"

sleep 1

# start clients
CLIENT_TOKEN_1=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "{\"room\": $WAITING_ROOM, \"task\": $TASK_ID, \"message_text\": true}" \
       $HOST:$PORT/api/v2/token | sed 's/^"\(.*\)"$/\1/')

echo "$HOST:$PORT/login/?next=%2F&name=client1&token=$CLIENT_TOKEN_1"

CLIENT_TOKEN_2=$(curl -X POST \
       -H "Authorization: Token $ADMIN_TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -d "{\"room\": $WAITING_ROOM, \"task\": $TASK_ID, \"message_text\": true}" \
       $HOST:$PORT/api/v2/token | sed 's/^"\(.*\)"$/\1/')

echo "$HOST:$PORT/login/?next=%2F&name=client1&token=$CLIENT_TOKEN_2"

docker logs -f audio-bot
