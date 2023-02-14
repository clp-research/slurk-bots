let golmi_socket = null
let layerView = null
let controller = null
let show_mouse = null


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


function start_golmi(url, password, role, tracking, show_gripped_objects) {
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

    if (role === "wizard"){
        layerView = new document.ReceiverLayerView(golmi_socket, bgLayer, objLayer, grLayer);
        grLayer.onclick = (event) => {
            console.log(event)
            socket.emit("mouse", {
                type: "click",
                coordinates: {"x": event.offsetX, "y": event.offsetY, "block_size": layerView.blockSize},
                element_id: "gripper",
                room: self_room
            });
        }

        // track mouse movements of the wizard on canvas
        trackMovement("gripper", 200);
        
    } else {
        layerView = new document.GiverLayerView(
            golmi_socket,
            bgLayer,
            objLayer,
            grLayer,
            show_gripped_objects
        );
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
function start(url, room_id, role, password, tracking, show_gripped_objects, warning) {
    console.log("received url")
    start_golmi(url, password, role, tracking, show_gripped_objects)
    golmi_socket.connect();
    golmi_socket.emit("join", { "room_id": room_id });

    // add warn user butto to wizard interface
    if (role === "wizard" && warning === true){
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
    }
}


function stop() {
    golmi_socket.disconnect();
}


function drawCircle(ctx, x, y, radius, fill, stroke, strokeWidth) {
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, 2 * Math.PI, false)

    if (fill) {
      ctx.fillStyle = fill
      ctx.fill()
    }

    if (stroke) {
      ctx.lineWidth = strokeWidth
      ctx.strokeStyle = stroke
      ctx.stroke()
    }
}


function confirm_selection(answer){
    socket.emit("message_command",
        {
            "command": {
                "event": "confirm_selection",
                "answer": answer
            },
            "room": self_room
        }
    )
}


$(document).ready(function () {
    socket.on("command", (data) => {
        if (typeof (data.command) === "object") {
            if (data.command.event === "init") {
                start(
                    data.command.url,
                    data.command.room_id,
                    data.command.role,
                    data.command.password,
                    data.command.tracking,
                    data.command.show_gripped_objects,
                    data.command.warning
                )
            }
        }
    });

    // listen for mouse events to plot mouse movements
    // socket.on("mouse", (data) => {
    //     if (my_role === "player"){
    //         if (data.type == "move"){ 
    //             canvas = $("#gripper")[0]
    //             console.log(data.coordinates)
    //             ctx = canvas.getContext("2d")
    //             ctx.clearRect(0, 0, canvas.width, canvas.height);
    //             drawCircle(ctx, data.coordinates.x, data.coordinates.y, 5, 'red', 'red', 2)
    //         }
    //     }
    // })
});
