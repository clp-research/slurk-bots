let session = [];
let golmi_socket_source = null
let golmi_socket_target = null
let targetlayerView = null
let sourcelayerView = null
let show_mouse = null


function start_golmi(url, password, role, room_id) {
    // --- create a golmi_socket --- //
    // don't connect yet

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


    // --- golmi_socket communication --- //
    golmi_socket_target.on("connect", () => {
        console.log("Connected to model server");
    });

    golmi_socket_target.on("disconnect", () => {
        console.log("Disconnected from model server");
    });

    golmi_socket_target.on("joined_room", (data) => {
        console.log(`Joined room ${data.room_id} as client ${data.client_id}`);
    })

    // for debugging: log all events
    golmi_socket_target.onAny((eventName, ...args) => {
        console.log(eventName, args);
    });

    golmi_socket_target.connect()
    golmi_socket_target.emit("join", { "room_id": `${room_id}_t` });

    if (role === "wizard"){
        golmi_socket_source = io(url, {
            auth: { "password": password }
        });
    
        // --- view --- // 
        // Get references to the three canvas layers
        let bgLayer = document.getElementById("source_background");
        let objLayer = document.getElementById("source_objects");
        let grLayer = document.getElementById("source_gripper");
    
        sourcelayerView = new document.CocoLayerView(
            golmi_socket_source,
            bgLayer,
            objLayer,
            grLayer
        );

        // --- golmi_socket communication --- //
        golmi_socket_source.on("connect", () => {
            console.log("Connected to model server");
        });

        golmi_socket_source.on("disconnect", () => {
            console.log("Disconnected from model server");
        });

        golmi_socket_source.on("joined_room", (data) => {
            console.log(`Joined room ${data.room_id} as client ${data.client_id}`);
        })

        // for debugging: log all events
        golmi_socket_source.onAny((eventName, ...args) => {
            console.log(eventName, args);
        });

        golmi_socket_source.connect()
        golmi_socket_source.emit("join", { "room_id": `${room_id}_s` });
        console.log(`${room_id}_s`)

        // if the gripper is used there is no need to track clicks
        grLayer.onclick = (event) => {
            console.log(event)
            socket.emit("mouse", {
                type: "click",
                coordinates: {"x": event.offsetX, "y": event.offsetY, "block_size": sourcelayerView.blockSize},
                element_id: "gripper",
                room: self_room
            });
        }
    }
}


function stop() {
    golmi_socket.disconnect();
}


function set_wizard(description) {
    $("#intro-image").hide();
    $("#source_card").show();
    $("#target_card").show();
    $("#instr_title").html("Wizard");
    $("#instr").html(description);
};


function set_player(description) {
    $("#intro-image").hide();
    $("#target_card").show();
    $("#instr_title").html("Player");
    $("#instr").html(description);
    $("#reference-grid").show();
    $("#terminal_card").hide();
};


function reset_role(description) {
    $("#intro-image").show();
    $("#source_card").hide();
    $("#target_card").hide();
    $("#instr_title").html("");
    $("#instr").html(description);
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


$(document).ready(() => {
    // send clear command and clear history box
    $('#clear_button').click(function(){
        socket.emit("message_command",
            {
                "command": {
                    "event": "clear_board",
                    "board": "target"
                },
                "room": self_room
            }
        )
        $("#history").text("")
    });


    $('#run_button').click(function(){
        // read input box and run commands one by one
        commands = $("#input").val().trim().split("\n")
        session = []
        console.log(commands)
        socket.emit("message_command",
            {
                "command": {
                    "event": "run",
                    "commands": commands
                },
                "room": self_room
            }
        )
    });

    $('#revert_button').click(function(){
        // make sure the history in not empty
        commands = [...session]
        empty_array = [""]
        is_empty = (
            commands.length === empty_array.length &&
            commands.every((item, idx) => item === empty_array[idx])
        )

        if (is_empty === false){
            socket.emit("message_command",
                {
                    "command": {
                        "event": "revert_session",
                        "command_list": commands
                    },
                    "room": self_room
                }
            )

            // move every command from history to the input field
            input = $("#input").val().trim().split("\n")
            input.forEach(element => {
                if(element !== ""){
                    commands.push(element)
                }
            })
            
            $("#input").val(commands.join("\n"))
            
            all_history = $("#history")[0].innerText.trim().split("\n")
            $("#history").text("")

            console.log(all_history)
            console.log(commands)
            for (let index = 0; index < all_history.length - commands.length; index++) {
                console.log(index)
                $('#history').append(`<b><code>${all_history[index]}<br/></code></b>`);
                $("#history").scrollTop($("#history")[0].scrollHeight);
            }
        }
    });

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
                        data.command.room_id,
                    );
                    break;

                case "reset_roles":
                    reset_role(data.command.instruction)
                    break;

                case "set_board":
                    if (data.command.name === "reference"){
                        $("#reference-grid").show();
                    }
                    // display_grid(data.command.board, data.command.name)
                    break;

                case "success_run":
                    $("#input").val("")
                    executed = data.command.executed
                    to_run = data.command.to_run
                    session.push(executed)

                    $('#history').append(`<b><code>${executed}<br/></code></b>`);
                    $("#history").scrollTop($("#history")[0].scrollHeight);
                    $("#input").val(to_run.join("\n"))
                    break;
            }
        }
    });
});
