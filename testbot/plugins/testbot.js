$(document).ready(function () {
    $("#submit").click( function(){
        message = $("#input_box").val();
        $("#result_box").val("you value was sent to the bot!")

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
            if (data.command.event === "reset") {
                $("#result_box").val("")
                $("#input_box").val("")
            }
        }
    });
})
