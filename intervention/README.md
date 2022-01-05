## Intervention Bot

This bot intercepts all messages sent by the users in a room while staying hidden. Messages are displayed as being sent by the users themselves. This allows modifying or hiding messages as required.

The bot works on a layout that treats all messages as commands, using the send-intercepted-message plugin. No special syntax is required for this, the idea is that users are not aware that their messages are altered. Users need to have the `send_command` permission.

The bot can be run with a command that follows the pattern:
```bash
docker run -e SLURK_TOKEN=c8469175-8e34-4c69-a2c7-472edce424b3 -e SLURK_USER=1 -e SLURK_PORT=5000 -e TASK_ID=1 --net="host" slurk/intervention-bot
```

The script `setup.sh` runs the server and bots locally. It must be run from the slurk/ directly, assuming that slurk/ and slurk-bots/ have the same parent directory.

The token needs to have at least the permissions `api`, `send_privately`, `send_message`. Please refer to <https://clp-research.github.io/slurk/slurk_multibots.html> for more detailed information. Images are currently not covered.

### Example

The example script modifies every other message, counting separately for each user. It takes the message, capitalizes the characters and reverses the string, then sends it on.

.. figure:: screenshot-example-intervention.png
   :align: center
   :scale: 25%

   The Intervention Bot intercepting every other message, counting for each user separately.

The logs show the bot as message sender. User messages are logged as commands.

This example extract corresponds to the screenshot above (bot id=2, user ids are 3 and 4)

```
{
  "data": {
    "broadcast": false,
    "command": "ah now I get it"
  },
  "date_created": "2022-01-05T09:41:10",
  "date_modified": null,
  "event": "command",
  "id": 23,
  "receiver_id": null,
  "room_id": 2,
  "user_id": 4
},
{
  "data": {
    "broadcast": false,
    "html": false,
    "message": "TI TEG I WON HA"
  },
  "date_created": "2022-01-05T09:41:10",
  "date_modified": null,
  "event": "text_message",
  "id": 24,
  "receiver_id": 3,
  "room_id": 2,
  "user_id": 2
},
{
  "data": {
    "broadcast": false,
    "command": "How are you?"
  },
  "date_created": "2022-01-05T09:41:01",
  "date_modified": null,
  "event": "command",
  "id": 21,
  "receiver_id": null,
  "room_id": 2,
  "user_id": 3
},
{
  "data": {
    "broadcast": false,
    "html": false,
    "message": "How are you?"
  },
  "date_created": "2022-01-05T09:41:01",
  "date_modified": null,
  "event": "text_message",
  "id": 22,
  "receiver_id": 4,
  "room_id": 2,
  "user_id": 2
},
{
  "data": {
    "broadcast": false,
    "command": "eh what?"
  },
  "date_created": "2022-01-05T09:40:56",
  "date_modified": null,
  "event": "command",
  "id": 19,
  "receiver_id": null,
  "room_id": 2,
  "user_id": 4
},
{
  "data": {
    "broadcast": false,
    "html": false,
    "message": "eh what?"
  },
  "date_created": "2022-01-05T09:40:56",
  "date_modified": null,
  "event": "text_message",
  "id": 20,
  "receiver_id": 3,
  "room_id": 2,
  "user_id": 2
},
{
  "data": {
    "broadcast": false,
    "command": "How are you"
  },
  "date_created": "2022-01-05T09:40:51",
  "date_modified": null,
  "event": "command",
  "id": 17,
  "receiver_id": null,
  "room_id": 2,
  "user_id": 3
},
{
  "data": {
    "broadcast": false,
    "html": false,
    "message": "UOY ERA WOH"
  },
  "date_created": "2022-01-05T09:40:51",
  "date_modified": null,
  "event": "text_message",
  "id": 18,
  "receiver_id": 4,
  "room_id": 2,
  "user_id": 2
},
{
  "data": {
    "broadcast": false,
    "command": "Hello"
  },
  "date_created": "2022-01-05T09:40:45",
  "date_modified": null,
  "event": "command",
  "id": 15,
  "receiver_id": null,
  "room_id": 2,
  "user_id": 3
},
{
  "data": {
    "broadcast": false,
    "html": false,
    "message": "Hello"
  },
  "date_created": "2022-01-05T09:40:45",
  "date_modified": null,
  "event": "text_message",
  "id": 16,
  "receiver_id": 4,
  "room_id": 2,
  "user_id": 2
},
```
