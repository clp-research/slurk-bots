function display_grid(grid, grid_name) {
    // clear grid div
    $(`#${grid_name}-grid`).empty();

    color_mapping = {
        "red": "#f44336",
        "blue": "#0080ff",
        "green": "#588F3A",
        "white": "white"
    }

    legend = {
        "○": "screw",
        "◊": "washer",
        "˂": "bridge (occupies 2 locations)",
        "□": "nut"
    }

    // define elements for padding
    alphabet_ints = Array.from(Array(26)).map((e, i) => i + 65);
    alphabet = alphabet_ints.map((x) => String.fromCharCode(x)); // [A..Z] 

    // add coordinates on upper header        
    var top_header = $("<tr>");
    for (let i = 0; i < grid[0].length + 1; i++) {
        var item = $("<th>");
        item.css({})
        if (i === 0) {
            item.text("");
            item.css({ "border": "3px solid white" })
        } else {
            item.text(i)
        }
        top_header.append(item)
    }
    $(`#${grid_name}-grid`).append(top_header);


    // create target
    for (let i = 0; i < grid.length; i++) {
        var div = $("<tr>");

        // header on the left
        if (grid_name === "target" || grid_name === "reference") {
            if ((i % 4) == 0) {
                var header = $("<th rowspan='4'>");
                header.text(alphabet[i / 4])
                header.css({
                    "background-color": "white"
                })
                div.append(header)
            }
        } else if (grid_name === "source") {
            var header = $("<th rowspan='1'>");
            header.text(alphabet[i])
            div.append(header)
        }

        // fill grid
        for (let j = 0; j < grid[i].length; j++) {
            var item = $("<td>").css({
                "background-color": color_mapping[grid[i][j][0]]
            });
            item.text(grid[i][j][1])
            item.attr("title", legend[grid[i][j][1]])
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
        if (typeof (data.command) === "object") {
            // assign role
            if ("role" in data.command) {
                if (data.command.role === "wizard") {
                    set_wizard(data.command.instruction)
                } else if (data.command.role === "player") {
                    set_player(data.command.instruction)
                } else if (data.command.role === "reset") {
                    reset_role(data.command.instruction)
                }

                // board update
            } else if ("board" in data.command) {
                display_grid(data.command.board, data.command.name)
                if (data.command.name === "target") {
                    display_grid(data.command.board, "reference")
                }
            }
        }
    });
});
