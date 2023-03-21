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

function start_golmi(url, password, role, show_gripper, show_gripped_objects) {
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

    controller = new document.LocalKeyController();

    if (role === "wizard"){
        layerView = new document.ReceiverLayerView(
            golmi_socket,
            bgLayer,
            objLayer,
            grLayer,
            show_gripped_objects,
            show_gripper
        );

        // if the gripper is used there is no need to track clicks
        if (show_gripper === false){
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
        }      

    } else {
        // give player possibility to click on objects to find out which one is the target
        grLayer.onclick = (event) => {
            socket.emit("mouse", {
                type: "click",
                coordinates: {"x": event.offsetX, "y": event.offsetY, "block_size": layerView.blockSize},
                element_id: "gripper",
                room: self_room
            });
        }
        layerView = new document.GiverLayerView(
            golmi_socket,
            bgLayer,
            objLayer,
            grLayer,
            show_gripped_objects,
            show_gripper
        );
    }
}


// --- stop and start drawing --- //
function start(url, room_id, role, password, show_gripper, show_gripped_objects, warning) {
    console.log("received url")
    start_golmi(url, password, role, show_gripper, show_gripped_objects)
    golmi_socket.connect();

    controller.resetKeys()
    controller.attachModel(golmi_socket);
   
    //golmi_socket.emit("add_gripper");
    golmi_socket.emit("join", { "room_id": room_id });

    if (role === "wizard"){
        golmi_socket.emit("add_gripper");
    }

    // create button for wizard and player
    if (role === "wizard" && warning === true){
        $("#generic_button").show()
        $("#generic_button").html("Send Warning")
        $('#generic_button').click(function(){
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
    } else if (role === "player"){
        $("#generic_button").show()
        $("#generic_button").html("Terminate Experiment")
        $('#generic_button').click(function(){
            console.log("aborting")
            socket.emit("message_command",
                {
                    "command": {
                        "event": "abort"
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

            switch(data.command.event){
                case "init":
                    start(
                        data.command.url,
                        data.command.room_id,
                        data.command.role,
                        data.command.password,
                        data.command.show_gripper,
                        data.command.show_gripped_objects,
                        data.command.warning
                    );
                    break;

                case "detach_controller":
                    console.log("detach")
                    controller.can_move = false;
                    break;

                case "attach_controller":
                    console.log("attach")
                    controller.can_move = true;
                    break;
            }
        }
    });
});