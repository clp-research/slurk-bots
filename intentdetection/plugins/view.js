


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
                    message = data.command.message
                    base64_encoded_string = message["target_board"]
                    $("#target-board-image").attr("src", "data:image/png;base64," + base64_encoded_string)

                    legend_encoded_string = message["legend_image"]
                    legend_caption = message["legend_caption"]
                    if (legend_encoded_string != null) {
                        console.log("legend is available, setting")
                        $("#target-board-legend").show()
                        $("#target-board-legend").attr("src", "data:image/png;base64," + legend_encoded_string)
                        console.log("setting legend caption")
                        $("#target-legend-caption").show()
                        //Get the legend caption
                        current_caption = "<a style='color:Maroon;'>Object Name: </a>"
                        update_caption = current_caption + legend_caption
                        $("#target-legend-caption").html(update_caption)
                    } else {
                        console.log("legend is not available, clearing")
                        $("#target-board-legend").hide()
                        $("#target-legend-caption").hide()
                    }
                        

                    break;
                case "close_after_10_images":
                    console.log("closing after 10 images")
                    $("#instruction").val("")
                    $("#target-board-image").attr("src", "https://media.giphy.com/media/tXL4FHPSnVJ0A/giphy.gif")
                    $("#button-submit").disabled = true
                    $("#target-board-caption").hide()
                    $("#target-board-legend").hide()
                    $("#target-legend-caption").hide()                    
                    break;
            }
        }
    });    
});