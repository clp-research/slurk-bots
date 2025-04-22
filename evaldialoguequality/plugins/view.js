


$(document).ready(function () {
    $("#button-next").click( function(){
        const selected = document.querySelector('input[name="dialogue-choice"]:checked');
        const value = selected ? selected.value : null;
        console.log("sending message: " + value);
        socket.emit("message_command",
            {
                "command": {
                    "event": "user_input",
                    "message": value
                },
                "room": self_room
            }
        )
    })

    socket.on("command", (data) => {
        if (typeof (data.command) === "object") {
            switch(data.command.event){
                case "set_dialogue":
                    console.log("clearing previous rating choices, if any")
                    document.querySelectorAll('input[name="dialogue-choice"]').forEach(radio => {
                        radio.checked = false;
                      });                    
                    console.log("setting the dialogue")
                    message = data.command.message
                    console.log('dialogue-1: ',message["dialogue_1"])
                    console.log('dialogue-2: ',message["dialogue_2"])
                    dialogue_1 = message["dialogue_1"]
                    dialogue_2 = message["dialogue_2"]
                    $("#dialogue-1").val(dialogue_1)
                    $("#dialogue-2").val(dialogue_2)
                    break;
                case "clear_dialogue":
                    console.log("received clear dialogue")
                    document.querySelectorAll('input[name="dialogue-choice"]').forEach(radio => {
                        radio.checked = false;
                      });
                    $("#dialogue-1").val("The task is now complete. You may close this window.");
                    $("#dialogue-2").val("The task is now complete. You may close this window.");
                    $("#button-next").hide();                                                         
            }
        }
    });    
});