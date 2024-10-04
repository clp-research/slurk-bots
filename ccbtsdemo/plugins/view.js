
function updateimage(base64_encoded_string) {
    console.log("Updating working board, with the new data");
    image_id = document.getElementById("working-board-image");
    console.log("Current image source: " + image_id.src)
    image_id.src = "data:image/png;base64," + base64_encoded_string;
    console.log("New image source: " + image_id.src);
    // Hidden the current world state image
    //image_id.style.display = "none";
    //$("#current-world-state").attr("src", filename);
}

function set_target_image(base64_encoded_string) {
    console.log("Setting the target board");
    image_id = document.getElementById("target-board-image");
    console.log("Current image source: " + image_id.src)
    image_id.src = "data:image/png;base64," + base64_encoded_string;
    console.log("New image source: " + image_id.src);

    //$("#current-world-state").attr("src", filename);
}

function confirm_undo(answer){
    socket.emit("message_command",
        {
            "command": {
                "event": "confirm_undo_intent",
                "answer": answer
            },
            "room": self_room
        }
    )
}


$(document).ready(function () {
    console.log("Document ready");
    $("#button-nextboard").click( function(){
        console.log("sending next board event");
        socket.emit("message_command",
            {
                "command": {
                    "event": "move_to_next_board",
                    "message": "moving to next board"
                },
                "room": self_room
            }
        )
    })

    $("#button-clearboard").click( function(){
        console.log("sending clear board event");
        socket.emit("message_command",
            {
                "command": {
                    "event": "clear_working_board",
                    "message": "clear working board"
                },
                "room": self_room
            }
        )
    })    

    socket.on("command", (data) => {
        console.log("Received command: " + JSON.stringify(data));
        if (typeof (data.command) === "object") {
            console.log("Command is an object", data);
            switch(data.command.event) {
                case "update_world_state":
                    console.log("Updating world state");
                    updateimage(data.command.message);
                    break;
                case "set_target_image":
                    console.log("Setting the target image");
                    set_target_image(data.command.message);
                    break;
                case "hide_working_board":
                    console.log("Hiding the working board");
                    image_id = document.getElementById("working-board-image");
                    image_id.style.display = "none";

                    image_caption_id = document.getElementById("working-board-caption");
                    image_caption_id.style.display = "none";

                    break;
            }
        }
    });
});