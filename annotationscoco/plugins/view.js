


$(document).ready(function () {
    $("#button-submit").click( function(){
        message = $("#instruction").val();
        console.log("sending message: " + message);
        socket.emit("message_command",
            {
                "command": {
                    "event": "user_input",
                    "message": message
                },
                "room": self_room
            }
        )
    })

    socket.on("command", (data) => {
        if (typeof (data.command) === "object") {
            switch(data.command.event){
                case "clear_text_area":
                    console.log("clearing text area")
                    $("#instruction").val("")
                    break;
                case "set_target_image":
                    console.log("setting target image")
                    base64_encoded_string = data.command.message
                    $("#target-board-image").attr("src", "data:image/png;base64," + base64_encoded_string)
                    break;
                case "close_after_10_images":
                    console.log("closing after 10 images")
                    $("#instruction").val("")
                    $("#target-board-image").attr("src", "https://media.giphy.com/media/tXL4FHPSnVJ0A/giphy.gif")
                    $("#button-submit").disabled = true
                    break;
            }
        }
    });    
});