
function updateimage(base64_encoded_string) {
    console.log("Updating working board, with the new data");
    image_id = document.getElementById("working-board-image");
    console.log("Current image source: " + image_id.src)
    image_id.src = "data:image/png;base64," + base64_encoded_string;
    console.log("New image source: " + image_id.src);

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


$(document).ready(() => {
    console.log("Document ready");
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
            }
        }
    });
});