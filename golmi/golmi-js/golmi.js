let golmi_socket = null
let layerView = null
let controller = null
let my_role = null


// copy some parts of the mouse tracking plugin
let trackMousePointer = {
    isMoving: false,
    pos: {x: undefined, y: undefined}
};

function trackGetPosition (evt, area) {
    let elem = document.getElementById(area);
    let position = elem.getBoundingClientRect();
    trackMousePointer.pos.x = evt.offsetX
    trackMousePointer.pos.y = evt.offsetY
}

function emitPosition(area) {
    if (trackMousePointer.isMoving) {
        socket.emit("mouse", {
           type: "move",
           coordinates: trackMousePointer.pos,
           element_id: area,
           room: self_room
	});
        trackMousePointer.isMoving = false;
    }
}

function trackMovement(area, interval) {
    $("#" + area).mousemove(function(e) {
        trackGetPosition(e, area);
        trackMousePointer.isMoving = true;
    });
    setInterval(emitPosition, interval, area);
}

function trackClicks(area) {
    $("#" + area).click(function(e) {
        trackGetPosition(e, area);
        
    });
}


function start_golmi(url, password, role) {
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

    console.log(role)

    if (role === "wizard"){
        layerView = new document.ReceiverLayerView(golmi_socket, bgLayer, objLayer, grLayer);
        $("#warning_button").show()
        $('#warning_button').click(function(){
            console.log("emitting warning")
            socket.emit("message_command",
                {
                    "command": {
                        "event": "warning"
                    },
                    "room": self_room
                }
            )
        });

        grLayer.onclick = (event) => {
            console.log(event)
            socket.emit("mouse", {
                type: "click",
                coordinates: {"x": event.offsetX, "y": event.offsetY, "block_size": layerView.blockSize},
                element_id: "gripper",
                room: self_room
            });
        }

        //track mouse movements
        // trackMovement("gripper", 200);

    } else {
        layerView = new document.GiverLayerView(golmi_socket, bgLayer, objLayer, grLayer);
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

    // for debugging: log all events
    golmi_socket.onAny((eventName, ...args) => {
        console.log(eventName, args);
    });
}


// --- stop and start drawing --- //
function start(url, room_id, role, password) {
    console.log("received url")
    start_golmi(url, password, role)
    golmi_socket.connect();
    golmi_socket.emit("join", { "room_id": room_id });

    // add warn user butto to wizard interface
    if (role === "wizard"){
        $("#wizard_interface").show();
    }
}


function stop() {
    golmi_socket.disconnect();
}


$(document).ready(function () {
    socket.on("command", (data) => {
        if (typeof (data.command) === "object") {
            if (data.command.event === "init") {
                my_role = data.command.role,
                start(
                    data.command.url,
                    data.command.room_id,
                    data.command.role,
                    data.command.password
                )
            }
        }
    });

    // listen for mouse events to plot mouse movements
    socket.on("mouse", (data) => {
        if (my_role === "player"){
            if (data.type == "move"){ 
                canvas = $("#gripper")[0]
                ctx = canvas.getContext("2d")
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.fillRect(data.coordinates.x, data.coordinates.y, 5, 5);
            }
        }
    })
});
