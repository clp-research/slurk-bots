var golmi_socket = null
var layerView = null
var controller = null
var demo_socket = null
var demo_layerView = null

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
                socket.emit("mouse", {
                    type: "click",
                    coordinates: {
                        "x": event.offsetX,
                        "y": event.offsetY,
                        "block_size": layerView.blockSize * layerView.grid_factor
                    },
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
                coordinates: {
                    "x": event.layerX,
                    "y": event.layerY,
                    "block_size": layerView.blockSize * layerView.grid_factor
                },
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

    $("#demo_view").remove()
    $("#task_view").show()

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


function reset_role() {
    golmi_socket.disconnect();
    $("#generic_button").hide()
    layerView = null
    controller = null
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


function start_demo(url, password, room_id){
    demo_socket = io(url, {
        auth: { "password": password }
    });
    // --- view --- // 
    // Get references to the three canvas layers
    let bgLayer = document.getElementById("background_demo");
    let objLayer = document.getElementById("objects_demo");
    let grLayer = document.getElementById("gripper_demo");

    demo_layerView = new document.ReceiverLayerView(
        demo_socket,
        bgLayer,
        objLayer,
        grLayer
    );

    demo_socket.connect();
  
    //golmi_socket.emit("add_gripper");
    demo_socket.emit("join", { "room_id": room_id});
}


$(document).ready(function () {
    socket.on("command", (data) => {
        if (typeof (data.command) === "object") {
            console.log(data)
            switch(data.command.event){
                case "init":
                    console.log("start")
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
                    console.log("detach controller")
                    controller.can_move = false;
                    break;

                case "attach_controller":
                    console.log("attach controller")
                    controller.can_move = true;
                    controller.resetKeys()
                    break;

                case "demo":
                    start_demo(
                        data.command.url,
                        data.command.password,
                        data.command.room
                    );
            }
        }
    });
});