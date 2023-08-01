let golmi_socket_working = null
let golmi_socket_target = null
let targetlayerView = null
let workinglayerView = null


function start_golmi(url, password, role, golmi_rooms) {
    // --- create a golmi_socket --- //
    // don't connect yet
    golmi_socket_working = io(url, {
        auth: { "password": password }
    });

    // --- view --- // 
    // Get references to the three canvas layers
    let bgLayer = document.getElementById("working_background");
    let objLayer = document.getElementById("working_objects");
    let grLayer = document.getElementById("working_gripper");

    workinglayerView = new document.CocoLayerView(
        golmi_socket_working,
        bgLayer,
        objLayer,
        grLayer
    );

    golmi_socket_working.connect()

    if (role === "wizard"){
        golmi_socket_working.emit("join", { "room_id": golmi_rooms.wizard_working });
        
        grLayer.onclick = (event) => {
            socket.emit("mouse", {
                type: "click",
                coordinates: {
                    event: "click",
                    button: "left",
                    x: event.offsetX,
                    y: event.offsetY,
                    block_size: workinglayerView.blockSize,
                    board: "wizard_working",
                    ctrl: event.ctrlKey
                },
                room: self_room
            });
        }

        // quick hack hide buttons
        $("#work_in_progress_button").hide()
        $("#inspect_button").hide()

        // right click
        grLayer.oncontextmenu = (event) => {
            socket.emit("mouse", {
                type: "click",
                coordinates: {
                    event: "click",
                    button: "right",
                    x: event.offsetX,
                    y: event.offsetY,
                    block_size: workinglayerView.blockSize,
                    board: "wizard_working",
                },
                room: self_room
            });
            return false
        }

        golmi_socket_target = io(url, {
            auth: { "password": password }
        });

        // --- view --- // 
        // Get references to the three canvas layers
        let bgLayer_t = document.getElementById("target_background");
        let objLayer_t = document.getElementById("target_objects");
        let grLayer_t = document.getElementById("target_gripper");
    
        targetlayerView = new document.CocoLayerView(
            golmi_socket_target,
            bgLayer_t,
            objLayer_t,
            grLayer_t
        );

        grLayer_t.onclick = (event) => {
            socket.emit("mouse", {
                type: "click",
                coordinates: {
                    event: "click",
                    x: event.offsetX,
                    y: event.offsetY,
                    block_size: targetlayerView.blockSize,
                    board: "wizard_selection"
                },
                room: self_room
            });
        }

        golmi_socket_target.connect()
        golmi_socket_target.emit("join", { "room_id": golmi_rooms.selector });
    }

    if (role === "player"){
        golmi_socket_working.emit("join", { "room_id": golmi_rooms.player_working });
        golmi_socket_target = io(url, {
            auth: { "password": password }
        });

        // --- view --- // 
        // Get references to the three canvas layers
        let bgLayer_t = document.getElementById("target_background");
        let objLayer_t = document.getElementById("target_objects");
        let grLayer_t = document.getElementById("target_gripper");

        targetlayerView = new document.CocoLayerView(
            golmi_socket_target,
            bgLayer_t,
            objLayer_t,
            grLayer_t
        );

        grLayer_t.onclick = (event) => {
            socket.emit("mouse", {
                type: "click",
                coordinates: {
                    event: "click",
                    x: event.offsetX,
                    y: event.offsetY,
                    block_size: targetlayerView.blockSize,
                    board: "player_target"
                },
                room: self_room
            });
        }

        golmi_socket_target.connect()
        golmi_socket_target.emit("join", { "room_id": golmi_rooms.target });
    }
}


function stop() {
    golmi_socket.disconnect();
}


function set_wizard(description) {
    $("#intro-image").hide();
    $("#golmi_card").show();
    $("#wizard_interface").show()
    $("#instr_title").html("Wizard");
    $("#instr").html(description);
    $("#variable_board_description").html("Source Board");
};


function set_player(description) {
    $("#intro-image").hide();
    $("#golmi_card").show();
    $("#player_interface").show()
    $("#variable_board_description").html("Target Board");
    $("#instr_title").html("Player");
    $("#instr").html(description);
};


function confirm_selection(answer){
    socket.emit("message_command",
        {
            "command": {
                "event": "confirm_next_episode",
                "answer": answer
            },
            "room": self_room
        }
    )
}


// add listener for each button
[
    "delete_object",
    "clear_board",
    "work_in_progress",
    "show_progress",
    "undo",
    "redo",
    "next_state",
    "revert_session",
    "inspect"
].forEach(element => {
    $(`#${element}_button`).click(() => {
        socket.emit("message_command",
            {
                command: {
                    event: element
                },
                room: self_room
            }
        )
    })
});


$(document).ready(() => {
    socket.on("command", (data) => {
        if (typeof (data.command) === "object") {
            // assign role
            switch(data.command.event){
                case "init":
                    if (data.command.role === "wizard") {
                        set_wizard(data.command.instruction)
                    } else if (data.command.role === "player"){
                        set_player(data.command.instruction)
                    }

                    start_golmi(
                        data.command.url,
                        data.command.password,
                        data.command.role,
                        data.command.golmi_rooms,
                    );
                    break;

                case "update_selectors":
                    shape = data.command.shape
                    color = data.command.color

                    $(`#shape_${shape}`).prop('checked', true);
                    $(`#color_${color}`).prop('checked', true);
                    clear_others(`shape_${shape}`)
                    clear_others(`color_${color}`);
                    break;

                case "typing":
                    socket.emit("keypress", {"typing": data.command.value})
                    break;

                case "instruction":
                    $("#instr").html(data.command.base);
                    data.command.extra.forEach(element => {
                        $('#instr').append("<hr>")
                        $('#instr').append(`<img id="theImg" src="${element}" />`)
                    });                    
                    break

                case "switch":
                    try{
                        golmi_socket_working.disconnect();
                        golmi_socket_target.disconnect();
                        targetlayerView.disconnect();
                        workinglayerView.disconnect();
                    } finally {
                        // reset interface
                        $("#intro-image").hide();
                        $("#golmi_card").hide();
                        $("#wizard_interface").hide()
                        $("#player_interface").hide()

                        if (data.command.role === "wizard") {
                            set_wizard(data.command.instruction)
                        } else if (data.command.role === "player"){
                            set_player(data.command.instruction)
                        }

                        start_golmi(
                            data.command.url,
                            data.command.password,
                            data.command.role,
                            data.command.golmi_rooms,
                        );
                    }
                    break;
            }
        }
    });
});
