$("#player_button").on('click', function(){
    console.log("player")
});

$("#wizard_button").on('click', function () {
    console.log("wizard")
});


function display_grid(data, grid_name){
    colors = ["red", "blue", "green", "orange"]

    // pad data
    x_source = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    x_target = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    y = [" ", "A", "B", "C", "D"]

    if (grid_name === "source"){
        data.unshift(x_source)
    } else {
        data.unshift(x_target)
    }

    for (let i=0; i<y.length; i++) {
        data[i].unshift(y[i])
    }

    // create grid based on data
    for (let i = 0; i < data.length; i++) {
        const div = document.createElement("div");
        div.setAttribute("class", "grid-row");

        for (let j=0; j<data[0].length; j++) {
            const item = document.createElement("div");
            item.setAttribute("class", "grid-item");

            if ((i == 0) || (j == 0)) {
                item.style.backgroundColor = "grey";
            } else {
                item.style.backgroundColor = colors[Math.floor((j-1)/3)];
            }

            item.innerHTML = data[i][j]
            div.append(item)
        }
        $(`#${grid_name}-grid`).append(div);
    }
}


data2 = [
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0, -1, -2],
    ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
]

// data will come from the bot
data = [
    [1, 2, 3, 4, 5, 6, 7, 8, 9],
    ["a", "b", "c", "d", "e", "f", "g", "h", "i"],
    [9, 8, 7, 6, 5, 4, 3, 2, 1],
    ["a", "b", "c", "d", "e", "f", "g", "h", "i"]
]


display_grid(data, "source")
display_grid(data2, "target")
$("#current-image").attr("src", "https://upload.wikimedia.org/wikipedia/commons/d/d8/Sailboat_Flat_Icon_Vector.svg")
