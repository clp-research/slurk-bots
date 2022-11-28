let golmi_socket = null
let layerView = null


function start_golmi(url, password) {
    // expect same as backend e.g. the default "http://127.0.0.1:5000";
    console.log(`Connect to ${url}`)

    // --- create a golmi_socket --- //
    // don't connect yet
    golmi_socket = io(url, {
        auth: { "password": password }
    });
    // debug: print any messages to the console
    localStorage.debug = 'golmi_socket.io-client:golmi_socket';

    // --- view --- // 
    // Get references to the three canvas layers
    let bgLayer = document.getElementById("background");
    let objLayer = document.getElementById("objects");
    let grLayer = document.getElementById("gripper");

    // Set up the view js, this also sets up key listeners
    layerView = new document.GiverLayerView(golmi_socket, bgLayer, objLayer, grLayer);
    function onMouseClick(event) {
        console.log(event)
        socket.emit("message_command",
            {
                "command": {
                    "event": "mouse_click",
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
    grLayer.onclick = onMouseClick

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

    // for debugging: log all events
    golmi_socket.onAny((eventName, ...args) => {
        console.log(eventName, args);
    });
}


// --- stop and start drawing --- //
function start(url, password, room_id) {
    console.log("received url")
    start_golmi(url, password)
    golmi_socket.connect();
    golmi_socket.emit("join", { "room_id": room_id });
}


function stop() {
    golmi_socket.disconnect();
}


$(document).ready(function () {
    console.log("document ready")
    $("#next").on('click', function () {
        socket.emit("message_command",
            {
                "command": {
                    "event": "next"
                },
                "room": self_room
            }
        )
    });


    socket.on("command", (data) => {
        console.log("receiving data")
        if (typeof (data.command) === "object") {
            if ("url" in data.command) {
                start(
                    data.command.url,
                    data.command.password,
                    data.command.room_id
                )
            }
        }
    });
});
