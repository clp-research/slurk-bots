$(document).ready(function () {

    socket.on("command", (data) => {
        if (typeof (data.command) === "object") {
            switch(data.command.event){
                case "send_instr":
                    $("#text_to_modify").html(data.command.message)
                    break;
                case "mark_target_grid":
                    $("#grid1_title").html(data.command.message)
                    break;
                case "update_grid1":
                    $("#grid1").html(data.command.message)
                    break;
                case "update_grid2":
                    $("#grid2").html(data.command.message)
                    break;
                case "update_grid3":
                    $("#grid3").html(data.command.message)
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