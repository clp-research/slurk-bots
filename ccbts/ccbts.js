let session = [];
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
                    x: event.offsetX,
                    y: event.offsetY,
                    block_size: workinglayerView.blockSize,
                    board: "wizard_working",
                },
                room: self_room
            });
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
    // $("#board_container").css({"display": "block"})
    //$("#working_board").css({"width": ""})
    //$("#target_board").hide();
    $("#instr_title").html("Wizard");
    $("#instr").html(description);
    $("#variable_board_description").html("Source Board");
};


function set_player(description) {
    $("#intro-image").hide();
    $("#golmi_card").show();
    $("#variable_board_description").html("Target Board");
    // $("#source_board").show();
    // $("#target_board").show();
    $("#instr_title").html("Player");
    $("#instr").html(description);
    // $("#reference-grid").show();
    // $("#terminal_card").hide();
};


function delete_object(){
    socket.emit("message_command",
        {
            command: {
                event: "delete_object"
            },
            room: self_room
        }
    )
}2


function show_progress(){
    socket.emit("message_command",
        {
            command: {
                event: "show_progress"
            },
            room: self_room
        }
    )
}


function clear_board(){
    socket.emit("message_command",
        {
            command: {
                event: "clear_board"
            },
            room: self_room
        }
    )
}


function work_in_progress(){
    socket.emit("message_command",
        {
            command: {
                event: "work_in_progress"
            },
            room: self_room
        }
    )
}


function on_checkbox_change(this_element){
    clear_others(this_element);
    parsed = this_element.split("_")
    value = parsed[1]

    if ($(`#action_place`).is(':checked') === true){
        return
    }

    // we allow to change the color
    if (["red", "blue", "yellow", "green"].includes(value)){
        socket.emit("message_command",
            {
                command: {
                    event: "update_object",
                    shape: get_propery("shape"),
                    color: get_propery("color"),
                },
                room: self_room
            }
        )
    }
}


function clear_others(this_element){
    options = {
        color: new Set(["red", "blue", "yellow", "green"]),
        shape: new Set(["screw", "bridge", "nut", "washer"]),
        action: new Set(["select", "place"])
    }

    // get info about this element
    parsed = this_element.split("_")
    element = parsed[0]
    value = parsed[1]

    // clear other options
    to_clear = options[element]
    to_clear.delete(value)
    to_clear.forEach(item => {
        $(`#${element}_${item}`).prop('checked', false);
    })
}


function get_propery(this_element){
    options = {
        color: ["red", "blue", "yellow", "green"],
        shape: ["screw", "bridge", "nut", "washer"],
        action: ["select", "place"]
    }

    for (let item of options[this_element]){
        if ($(`#${this_element}_${item}`).is(':checked')){
            return item
        }
    }
}

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
                    clear_others(`color_${color}`)
            }
        }
    });
});
