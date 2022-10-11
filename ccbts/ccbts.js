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

            if ("role" in data.command){
                console.log("role")
                console.log(data.command)

                if (data.command.role === "wizard"){
                    set_wizard(data.command.instruction)
                } else {
                    set_player(data.command.instruction)
                }
            } else if ("board" in data.command) {

                console.log("SEE MY BOARD");
                console.log(data.command);
                display_grid(data.command.board, data.command.name)
            }
        }
    });
    
    function display_grid(grid, grid_name) {
        // define elements for padding
        colors = ["red", "blue", "green", "orange"]  //TODO: this list should be longer
        alphabet_ints = Array.from(Array(26)).map((e, i) => i + 65);
        alphabet = alphabet_ints.map((x) => String.fromCharCode(x)); // [A..Z] used for y coordinates
        alphabet.unshift(" ")  // add empty space for padding
        numbers = Array.from(Array(26).keys(), n => n + 1); // [1..26] used for x coordinates

        // pad grid
        grid.unshift(numbers.slice(0, grid[0].length))
        for (let i = 0; i < grid.length; i++) {
            grid[i].unshift(alphabet[i])
        }

        // create grid 
        for (let i = 0; i < grid.length; i++) {
            const div = document.createElement("div");
            div.setAttribute("class", "grid-row");

            for (let j = 0; j < grid[0].length; j++) {
                const item = document.createElement("div");
                item.setAttribute("class", "grid-item");

                if ((i == 0) || (j == 0)) {
                    item.style.backgroundColor = "grey";
                } else {
                    item.style.backgroundColor = colors[j - 1];
                }

                item.innerHTML = grid[i][j]
                div.append(item)
            }
            $(`#${grid_name}-grid`).append(div);
        }
    };

    function set_wizard(description) {
        $("#buttons").hide();
        $("#source_card").show();
        $("#target_card").show();
        $("#instr_title").html("Wizard");
        $("#instr").html(description);
    };

    function set_player(description) {
        $("#buttons").hide();
        $("#image_card").show();
        $("#target_card").show();
        $("#instr_title").html("Player");
        $("#instr").html(description);
    };
});
