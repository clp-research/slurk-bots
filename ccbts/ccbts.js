function display_grid(grid, grid_name) {
    // clear grid div
    $(`#${grid_name}-grid`).empty();
    $(`#${grid_name}-header`).empty();

    // define elements for padding
    alphabet_ints = Array.from(Array(26)).map((e, i) => i + 65);
    alphabet = alphabet_ints.map((x) => String.fromCharCode(x)); // [A..Z] 
    alphabet.unshift("")

    // create left header
    for (let i = 0; i < grid.length + 1; i++) {
        let item = document.createElement("div");
        item.setAttribute("class", "grid-header");

        if (alphabet[i] === "") {
            item.innerHTML = "&nbsp;"
        } else {
            item.innerHTML = alphabet[i]
        }

        $(`#${grid_name}-header`).append(item)
    }

    // add coordinates on upper header
    numbers = Array.from(Array(26).keys(), n => ["grey", n + 1]); // [1..26] used         
    if (grid_name === "target") {
        reducing_factor = 4
    } else {
        reducing_factor = 3
    }

    grid.unshift(numbers.slice(0, Math.floor((grid[0].length) / reducing_factor)))

    // create grid 
    for (let i = 0; i < grid.length; i++) {
        let div = document.createElement("div");
        div.setAttribute("class", "grid-row");

        for (let j = 0; j < grid[i].length; j++) {
            let item = document.createElement("div");
            item.setAttribute("class", "grid-item");

            item.style.backgroundColor = grid[i][j][0]

            if (grid[i][j][1] === "") {
                item.innerHTML = "&nbsp;"
            } else {
                item.innerHTML = grid[i][j][1]
            }
            div.append(item)
        }
        $(`#${grid_name}-grid`).append(div);
    }
};


function set_wizard(description) {
    $("#intro-image").hide();
    $("#source_card").show();
    $("#target_card").show();
    $("#instr_title").html("Wizard");
    $("#instr").html(description);
};


function set_player(description) {
    $("#intro-image").hide();
    $("#image_card").show();
    $("#target_card").show();
    $("#instr_title").html("Player");
    $("#instr").html(description);
};


function reset_role(description) {
    $("#intro-image").show();
    $("#image_card").hide();
    $("#source_card").hide();
    $("#target_card").hide();
    $("#instr_title").html("");
    $("#instr").html(description);
}


$(document).ready(() => {
    $("#player_button").on('click', function () {
        socket.emit("message_command",
            {
                "command": "set_role_player",
                "room": self_room 
            }
        )
    });

    $("#wizard_button").on('click', function () {
        socket.emit("message_command",
            {
                "command": "set_role_wizard",
                "room": self_room
            }
        )
    });

    socket.on("command", (data) => {
        if (typeof(data.command) === "object"){
            // assign role

            console.log(data)

            if ("role" in data.command){
                if (data.command.role === "wizard"){
                    set_wizard(data.command.instruction)
                } else if (data.command.role === "player") {
                    set_player(data.command.instruction)
                } else if (data.command.role === "reset") {
                    reset_role(data.command.instruction)
                }

            // board update
            } else if ("board" in data.command) {
                console.log("SEE MY BOARD");
                console.log(data.command);
                display_grid(data.command.board, data.command.name)
            }
        }
    });
});
