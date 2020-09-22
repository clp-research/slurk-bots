let gameStarted = false;
let trackingArea = "#current-image"
let mouse = {
    click: false,
    move: false,
    pos: {x:false, y:false}
};
let scaleFactor = {x:undefined, y:undefined};
let mousePositions = [];
/*
var audioDescription = document.getElementById('audio-description');
var audioCorrect = document.getElementById('audio-correct');
var audioFalse = document.getElementById('audio-false');
*/
let image = document.getElementById("current-image")
var imgWrapper = document.getElementById('image-wrapper');
var sidebar = document.getElementById('sidebar');

/*
    ***Event listener***
*/

/*
audioDescription.addEventListener("play", function(){emitAudioEvent(audioDescription)}, false);
audioCorrect.addEventListener("play", function(){emitAudioEvent(audioCorrect)}, false);
audioFalse.addEventListener("play", function(){emitAudioEvent(audioFalse)}, false);
*/

document.addEventListener("fullscreenchange", fullscreenChange );
document.addEventListener("mozfullscreenchange", fullscreenChange()); // Firefox
document.addEventListener("webkitfullscreenchange", fullscreenChange()); // Safari/Opera
document.addEventListener("msfullscreenchange", fullscreenChange()); // IE/Edge

window.addEventListener('touchstart', function() {
    /* write log entry if user uses touch */
  socket.emit('log', {
      type: "touch_event",
      data: {
          timestamp:Date.now()
      },
      room: self_room});
});

/*
    ***Function definitions***
*/

function emitAudioEvent(element){
    /*
    write log entry if audio file is played.
    the audio playback itself is triggered by the event handlers defined above.
    */
    socket.emit('log', {
        type: "audio_playback",
        data: {
            timestamp:Date.now(),
            element:"#"+element.id
        },
        room: self_room});
}

function getImageScaleFactor(img) {
    /*
    return image scale factor
    */
    scaleFactor.x = img.width / img.naturalWidth;
    scaleFactor.y = img.height / img.naturalHeight;
}

function getPosition (evt, area) {
    /*
    assign current mouse position within an area to mouse.pos
    */
    position = $(area).offset();
    mouse.pos.x = (evt.clientX - position.left) / scaleFactor.x;
    mouse.pos.y = (evt.clientY - position.top) / scaleFactor.y;
}

function storePosition(a, intrvl) {
    /*
    add the current mouse position to the mousePositions array
    */
    if (mouse.move) {
        mousePositions.push({
            timestamp:Date.now(),
            x:mouse.pos.x,
            y:mouse.pos.y
        });
        mouse.move = false;
    }
}

function trackMovement(area,interval) {
    /*
    retrieve and store cursor position on movement within a defined area
    in a defined interval
    */
    $(area).mousemove(function(e){
        getPosition(e, area);
        mouse.move = true;
    });
    setInterval(storePosition,interval,area)
}

function centerImage() {
    /*
    horizontally center image
    */
    imgWrapper.style.left = ((sidebar.offsetWidth/2)-(imgWrapper.offsetWidth/2));
}

function enterFullscreen(element) {
    /*
    request fullscreen mode
    */
    if(element.requestFullscreen) {
        element.requestFullscreen();
        // cross browser compatibility for Firefox; Chrome/Safari/Opera; IE/Edge
    } else if(element.mozRequestFullScreen) {
        element.mozRequestFullScreen();
    } else if(element.webkitRequestFullscreen) {
        element.webkitRequestFullscreen();
    } else if(element.msRequestFullscreen) {
        element.msRequestFullscreen();
    }
}

function closeFullscreen() {
    /*
    disable fullscreen mode
    */
    if (document.exitFullscreen) {
        document.exitFullscreen();
        // cross browser compatibility for Firefox; Chrome/Safari/Opera; IE/Edge
    } else if (document.mozCancelFullScreen) {
        document.mozCancelFullScreen();
    } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
    } else if (document.msExitFullscreen) {
        document.msExitFullscreen();
    }
}

function fullscreenStatus(){
    /*
    return true if browser is in fullscreen mode
    */
    if (
        document.fullscreenElement ||
        // cross browser compatibility for Firefox; Chrome/Safari/Opera; IE/Edge
        document.mozFullScreenElement ||
        document.webkitFullscreenElement ||
        document.msFullscreenElement
    ) {
        return true;
    } else {
        return false;
    }
}

function fullscreenChange () {
    /*
    display overlay if user disables fullscreen mode and game has started
    */
    if (gameStarted == true) {
        if (fullscreenStatus() == true) {
            console.log("fullscreen enabled")
            $("#fullscreen-overlay").fadeOut();
        } else {
            console.log("fullscreen disabled")
            $("#fullscreen-overlay").fadeIn();
            $("#fullscreenButton").fadeIn();
        }
    }
}

function logMouseData() {
    /*
    dispay image overlay and emit all mouse positions collected
    for the current image
    */
    $("#image-overlay").fadeIn(200);
    $(".img-button").fadeOut(200);
    console.log("logging tracking data");
    socket.emit('log', {type: "mouse_positions", data:mousePositions, room: self_room});
    mousePositions = [];
}

/*
    ***Socket events***
*/

socket.on('message', function(data) {
    /*
    actions triggered by room messages sent by game bot
    action depend on message text
    */
    if (data.user.name == "ImageClick_Main" || data.user.name == "ImageClick_Pretest") {
        console.log("message from image click bot: ", data.msg)
        switch(data.msg) {
            case "Correct!":
                // play audio, log tracking data, show overlay
                audioCorrect.play();
                logMouseData();
                break;
            case "Try again!":
                audioFalse.play();
                break;
            case "Skipping Image":
                logMouseData();
                break;
            case "Game started!":
                gameStarted = true;
                audioCorrect.src="/static/audio/correct.wav";
                audioFalse.src="/static/audio/tryagain.wav";
                console.log("game started:", gameStarted);
                break;
            case "No images left":
                closeFullscreen();
                gameStarted = false;
                $(".overlay").hide();
                console.log("game started:", gameStarted);
                break;
        }
    }
    // return if message is from client
    if (self_user.id == data.user.id) return;
    if (data["image"] !== undefined) {
        display_image(data.user, data.timestamp, data.image, data.width, data.height, data.privateMessage);
    }
});

socket.on('attribute_update', function(data) {
    /*
        if new audio & image urls are sent by the bot:
        show image overlay and hide replay & report buttons
    */
    console.log("new image:",data,"Game started:",gameStarted)
    if (gameStarted==true && data.id == 'audio-description') {
        $(".overlay").show();
        $(".img-button").hide();
    }
  });

socket.on('text_update', function(data) {
    /*
        if content of overlay-textbox is updated by the bot:
        show overlays and text box
    */
    if (data.id='overlay-textbox') {
        $('#fullscreen-overlay').show();
        $('#text-overlay').show();
    }
});

/*
    ***button actions***
*/

$('.button').click(function(e){
    /* assign coordinates of the button's center point to mouse.pos and emit events*/
    getPosition(e, trackingArea)
    console.log("click on "+e.target.id)
    socket.emit('mousePosition', {
        type:'click',
        element:"#"+e.target.id,
        coordinates:mouse.pos,
        room: self_room
    });
    socket.emit('log', {
        type: "mouse_click",
        data: {
            timestamp:Date.now(),
            coordinates:mouse.pos,
            element:"#"+e.target.id
        },
        room: self_room
    });
    /* button action depending on id */
    switch(e.target.id) {
        /* overlay button: hide overlay, show image buttons and play audio file */
        case "overlayButton":
            $(".overlay").fadeOut(200);
            $(".img-button").fadeIn(200);
            /* play transmitted audio file after 500 ms */
            setTimeout(function(){
                audioDescription.play();}, 500);
            break;
        /* replay button: play audio */
        case "replayButton":
            audioDescription.play();
            break;
        /* report button: ask client to confirm; write to log; emit mouse data */
        case "reportButton":
            if (confirm("Using the report button will be logged! Are you shure you want to proceed?")==true){
                socket.emit('log', {
                    type: "mouse_click",
                    data: {
                        timestamp:Date.now(),
                        element:"confirmReportButton",
                        coordinates:mouse.pos
                    },
                    room: self_room
                });
                logMouseData();
                socket.emit('mousePosition', {
                    type:'click',
                    element:"confirmReportButton",
                    coordinates:mouse.pos,
                    room: self_room
                });
              }
            else {
              socket.emit('log', {
                  type: "mouse_click",
                  data: {
                      timestamp:Date.now(),
                      element:"cancelReportButton",
                      coordinates:mouse.pos
                  },
                  room: self_room
              });
            }
            break;
        /* fullscreen button: enter fullscreen mode */
        case "fullscreenButton":
            enterFullscreen(document.documentElement);
            break;
        /* start button: hide startButton; enter fullscreen mode */
        case "startButton":
            $("#startButton").fadeOut(200);
            enterFullscreen(document.documentElement);
            break;
    }
});

/*
    ***other events & initial setup***
*/

// activate mouse tracking
trackMovement(trackingArea, 10);

// add preload and type attributes to audio elements
/*$(".audio").attr({
    preload:"auto",
    type:"audio/wav"
});*/

// center image if new image is loaded or window is resized
image.onload = function () {
    getImageScaleFactor(image);
    centerImage();
}
window.onresize = function () {
    getImageScaleFactor(image);
    centerImage();
};

// emit mousePosition event and log position if user clicks on the image
$("#current-image").click(function(e){
    getPosition(e, "#current-image");
    socket.emit('mousePosition', {
        type:'click',
        element:"#current-image",
        coordinates:mouse.pos,
        room: self_room
    });
    socket.emit('log', {
        type: "mouse_click",
        data: {
            timestamp:Date.now(),
            coordinates:mouse.pos,
            element:"#current-image"
        },
        room: self_room});
    });
