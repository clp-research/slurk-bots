let golmi_socket = null
let layerView = null
let controller = null

function start_golmi(url, role) {
    // expect same as backend e.g. the default "http://127.0.0.1:5000";
    console.log(`Connect to ${url}`)

    // --- create a golmi_socket --- //
    // don't connect yet
    golmi_socket = io(url, {
        auth: { "password": "GiveMeTheBigBluePasswordOnTheLeft" }
    });
    // debug: print any messages to the console
    localStorage.debug = 'golmi_socket.io-client:golmi_socket';

    // --- view --- // 
    // Get references to the three canvas layers
    let bgLayer = document.getElementById("background");
    let objLayer = document.getElementById("objects");
    let grLayer = document.getElementById("gripper");
    
    // set up controller
    controller = new document.LocalKeyController();
    // Set up the view js, this also sets up key listeners

    console.log(role)

    if (role === "wizard"){
        layerView = new document.ReceiverLayerView(golmi_socket, bgLayer, objLayer, grLayer);
    } else {
        layerView = new document.GiverLayerView(golmi_socket, bgLayer, objLayer, grLayer);
    }
    
    
    grLayer.onclick = (event) => {
        console.log(event.x, event.y)
        console.log(event.target)
        console.log(socket)

        socket.emit("message_command",
            {
                "command": {
                    "target_id": event.target.id,
                    "offset_x": event.offsetX,
                    "offset_y": event.offsetY,
                    "x": event.x,
                    "y": event.y,
                    "block_size": layerView.blockSize,
                },
                "room": self_room
            }
        )
    }

    // --- golmi_socket communication --- //
    golmi_socket.on("connect", () => {
        console.log("Connected to model server");
    });

    golmi_socket.on("disconnect", () => {
        console.log("Disconnected from model server");
    });

    golmi_socket.on("joined_room", (data) => {
        console.log(`Joined room ${data.room_id} as client ${data.client_id}`);
    })

    var setup_complete = false;


    // for debugging: log all events
    golmi_socket.onAny((eventName, ...args) => {
        console.log(eventName, args);
    });

    function custom_config_is_applied(custom_config, config_update) {
        return Object.keys(custom_config).every(key => {
            return config_update[key] == custom_config[key];
        });
    }
}


// --- stop and start drawing --- //
function start(url, room_id, role) {
    console.log("received url")
    start_golmi(url, role)
    
    // reset the controller in case any key is currently pressed
    controller.resetKeys()
    controller.attachModel(golmi_socket);
    // manually establish a connection, connect the controller and load a state
    golmi_socket.connect();
    golmi_socket.emit("join", { "room_id": room_id });
}

function stop() {
    // reset the controller in case any key is currently pressed
    controller.resetKeys();
    // disconnect the controller
    controller.detachModel(golmi_socket, "0");
    // manually disconnect
    golmi_socket.disconnect();
}



$(document).ready(function () {
    console.log("starting")
    socket.on("command", (data) => {
        if (typeof (data.command) === "object") {
            // assign role
            // if ("role" in data.command) {
            //     if (data.command.role === "wizard") {
            //         set_wizard(data.command.instruction)
            //     } else if (data.command.role === "player") {
            //         set_player(data.command.instruction)
            //     } else if (data.command.role === "reset") {
            //         reset_role(data.command.instruction)
            //     }

                // board update
            // } else 
            if ("url" in data.command) {
                start(
                    data.command.url,
                    data.command.room_id,
                    data.command.role
                )
            }
        }
    });
}); // on document ready end
