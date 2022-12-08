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

    var table = $("<table>");
    table.css({ "style": "width: 100%", "height": "100%" })

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
    table.append(top_header);


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

            txt = grid[i][j][1]

            // replace empty cells to preserve dimensions
            if (txt === ""){
                txt = "|"
                item.css({"color": "white"})
            }

            item.text(txt)
            item.attr("title", legend[grid[i][j][1]])
            div.append(item)
        }
        table.append(div)
    }


    card_header = $(`<div>${grid_name.toUpperCase()} BOARD</div>`);
    card_header.css({ "text-align": "center", "font-weight": "bold" })

    hr = $("<hr>");
    hr.css({ "margin": "10px 2px", "background-color": "#abb2b9", "opacity": ".50;" })

    header_div = $("<div>");
    header_div.css({ "style": "width: 100%", "height": "7%" })
    header_div.append(card_header)
    header_div.append(hr)

    center = $("<center>");
    center.css({ "style": "width: 100%", "height": "93%" })
    center.append(table)

    $(`#${grid_name}-grid`).append(header_div);
    $(`#${grid_name}-grid`).append(center);
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
    $("#target_card").show();
    $("#instr_title").html("Player");
    $("#instr").html(description);
    $("#reference-grid").show();
    $("#terminal_card").hide();
};


function reset_role(description) {
    $("#intro-image").show();
    $("#source_card").hide();
    $("#target_card").hide();
    $("#instr_title").html("");
    $("#instr").html(description);
}


$(document).ready(() => {
    $('#clear_button').click(function(){
        socket.emit("message_command",
            {
                "command": {
                    "event": "clear_board",
                    "board": "target"
                },
                "room": self_room
            }
        )
    });

    $('#run_button').click(function(){
        commands = $("#input").val().trim()
        socket.emit("message_command",
            {
                "command": {
                    "event": "run",
                    "command_string": commands
                },
                "room": self_room
            }
        )
    });

    $('#revert_button').click(function(){
        commands = $("#history").children().text()
        console.log(commands)
        socket.emit("message_command",
            {
                "command": {
                    "event": "revert_session",
                    "command_list": commands
                },
                "room": self_room
            }
        )
        $("#input").val(commands.split(";").join(";\n"))
        $("#history").text("")
    });
    
    socket.on("command", (data) => {
        if (typeof (data.command) === "object") {
            // assign role
            this_event = data.command.event
            if (this_event === "assign_role"){
                if (data.command.role === "wizard") {
                    set_wizard(data.command.instruction)
                } else if (data.command.role === "player"){
                    set_player(data.command.instruction)
                }

            // reset roles
            } else if (this_event === "reset_roles") {
                reset_role(data.command.instruction)

            // board update
            } else if (this_event === "set_board") {
                if (data.command.name === "reference"){
                    $("#reference-grid").show();
                }
                display_grid(data.command.board, data.command.name)

            // commands were successfull, clear session
            } else if (this_event === "end_session"){
                $("#history").text("")
                commands = $("#input").val().trim().split("\n")
                commands.forEach(element => {
                    $('#history').append(`<b><code>${element}<br/></code></b>`);
                    $("#history").scrollTop($("#history")[0].scrollHeight);
                });
                $("#input").val("")
            }
        }
    });
});
