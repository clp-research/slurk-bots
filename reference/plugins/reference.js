$(document).ready(function () {

    socket.on("command", (data) => {
        if (typeof (data.command) === "object") {
            switch(data.command.event){
                case "send_instr":
                    $("#text_to_modify").html(data.command.message)
                    break;
            }
        }
    });
})

function confirm_ready(answer){
    socket.emit("message_command",
        {
            "command": {
                "event": "confirm_ready",
                "answer": answer
            },
            "room": self_room
        }
    )
}