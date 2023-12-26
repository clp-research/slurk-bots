const NUMBER_OF_GUESSES = 6;
const NUMBER_OF_ROWS = 5;
const NUMBER_OF_COLUMNS = 5;
let guessesRemaining = NUMBER_OF_GUESSES;
let currentGuess = [];
let nextLetter = 0;
let submitted = false;  // whether a guess was submitted
let selected_cell = null;  // keep track of the box the user selects

// Initialize a 2D array to represent the grid
let grid = Array.from({ length: NUMBER_OF_ROWS }, () => Array(NUMBER_OF_COLUMNS).fill('▢'));

function initBoard() {
    let board = document.getElementById("game-board");
    board.textContent = "";

    for (let i = 0; i < NUMBER_OF_ROWS; i++) {
        let row = document.createElement("div")
        row.className = "letter-row"

        for (let j = 0; j < 5; j++) {
            let box = document.createElement("div")
            box.className = "letter-box"

            // click listener: if the user clicks on this cell, make it the selected_cell
            box.onclick = function(){
                if (selected_cell !== null){
                    selected_cell.style["boxShadow"] = ""
                }
                selected_cell = this;
                selected_cell.style["boxShadow"] = "1px 1px 2px 2px #00305E, -1px -1px 2px 2px #00305E"
            };
            row.appendChild(box)
        }
        board.appendChild(row)
    }
    for (const elem of document.getElementsByClassName("keyboard-button")) {
        elem.style.backgroundColor = "";
    }
}


function deleteLetter() {
    let row = document.getElementsByClassName("letter-row")[6 - guessesRemaining]
    let box = row.children[nextLetter - 1]
    if (box){
        box.textContent = ""
        box.classList.remove("filled-box")
        currentGuess.pop()
        nextLetter -= 1
    }
}


function checkGuess(guessString, rightWordString) {
    let row = document.getElementsByClassName("letter-row")[6 - guessesRemaining]
    let rightGuess = Array.from(rightWordString)

    let colors = ["", "", "", "", ""];
    let remaining = Array.from(rightWordString)

    // first check for green letters
    for (let i = 0; i < 5; i++) {
        let guessLetter = guessString.charAt(i);
        let solutionLetter = rightGuess[i];
        if (guessLetter === solutionLetter) {
            colors[i] = "green";
            remaining[i] = " ";
        }
    }

    // check for yellows and greys
    for (let i = 0; i < 5; i++) {
        let guessLetter = guessString.charAt(i);

        if (remaining.includes(guessLetter) === true) {
            if (colors[i] === "") {
                colors[i] = "yellow";

                // remove this letter from remaining
                to_remove_index = remaining.indexOf(guessLetter)
                remaining.splice(to_remove_index, 1)
            }
        } else {
            if (colors[i] === "") {
                colors[i] = "grey";
            }
        }
    }

    for (let i = 0; i < 5; i++) {
        let box = row.children[i]
        let delay = 250 * i
        setTimeout(() => {
            // flip box
            animateCSS(box, 'flipInX')
            // shade box
            box.style.backgroundColor = colors[i]
            // prevent user's shenanigans
            box.textContent = guessString[i]
//            shadeKeyBoard(guessString[i], colors[i])
        }, delay)
    }
    // update game variables
    guessesRemaining -= 1;
    currentGuess = [];
    nextLetter = 0;
}


function insertLetter(pressedKey) {
    pressedKey = pressedKey.toLowerCase()

    // add this letter to the selected cell
    let box = selected_cell

    animateCSS(box, "pulse")
    box.textContent = pressedKey
    box.classList.add("filled-box")
    currentGuess.push(pressedKey)

    // Calculate the row and column based on the selected_cell
    let rowIndex = Array.from(selected_cell.parentElement.parentElement.children).indexOf(selected_cell.parentElement);
    let colIndex = Array.from(selected_cell.parentElement.children).indexOf(selected_cell);

    // Ensure the currentGuess array has enough rows
    if (!currentGuess[rowIndex]) {
        currentGuess[rowIndex] = [];
    }

    // Set the pressedKey at the correct position in currentGuess
    currentGuess[rowIndex][colIndex] = pressedKey;

    console.log(`Inserting letter: ${pressedKey} at row: ${rowIndex} and column: ${colIndex}`);
}


const animateCSS = (element, animation, prefix = 'animate__') =>
    // We create a Promise and return it
    new Promise((resolve, reject) => {
        const animationName = `${prefix}${animation}`;
        // const node = document.querySelector(element);
        const node = element
        node.style.setProperty('--animate-duration', '0.3s');

        node.classList.add(`${prefix}animated`, animationName);

        // When the animation ends, we clean the classes and resolve the Promise
        function handleAnimationEnd(event) {
            event.stopPropagation();
            node.classList.remove(`${prefix}animated`, animationName);
            resolve('Animation ended');
        }
        node.addEventListener('animationend', handleAnimationEnd, { once: true });
    });


function sendGuess() {
    let guessString = '';

// SOLUTION A
//    for (let i = 0; i < NUMBER_OF_ROWS; i++) {
//        for (let j = 0; j < 5; j++) {
//            if (currentGuess[i] && currentGuess[i][j]) {
//                guessString += currentGuess[i][j];
//            } else {
//                guessString += '▢'; // Empty space for not guessed letters
//            }
//        }
//    }

//SOLUTION B
//    // Initialize all cells with empty space
//    let emptyRow = Array(5).fill('▢');
//    for (let i = 0; i < NUMBER_OF_ROWS; i++) {
//        let row = currentGuess[i] ? [...currentGuess[i]] : emptyRow;
//
//        // Ensure the row has exactly 5 elements
//        row = row.concat(Array(Math.max(0, 5 - row.length)).fill('▢'));
//
//        guessString += row.join('');
//    }

    // Iterate through each row in the grid
    for (let i = 0; i < NUMBER_OF_ROWS; i++) {
        let row = currentGuess[i] || Array(5).fill('▢'); // Use currentGuess[i] if available, otherwise use an empty row

        // Ensure the row is an array
        if (!Array.isArray(row)) {
            row = Array(5).fill('▢'); // Use an empty row if currentGuess[i] is not an array
        }
        // Ensure the row has exactly 5 elements
        row = row.concat(Array(Math.max(0, 5 - row.length)).fill('▢'));

        // Log the row and its index
        console.log(`Row ${i}: ${row.join('')}`);

        guessString += row.join('');
    }

    // Log the final guessString
    console.log(`Final Guess: ${guessString}`);


    socket.emit("message_command",
        {
            "command": {
                "guess": guessString,
                "remaining": guessesRemaining
            },
            "room": self_room
        }
    );
}


function getKeyPressed(letter) {
    if (guessesRemaining === 0) {
        return
    }

    let pressedKey = String(letter)

    if (pressedKey === "DEL" && nextLetter !== 0 && !submitted) {
        deleteLetter()
        return
    }

    if (pressedKey === "ENTER") {
        submitted = true;
        sendGuess()
        return
    }

    let found = pressedKey.match(/[a-z]/gi)
    if (!found || found.length > 1) {
        return
    } else {
        insertLetter(pressedKey)
    }
}


document.getElementById("keyboard-cont").addEventListener("click", (e) => {
    const target = e.target
    let key = target.textContent.trim()

    if (!target.classList.contains("keyboard-button")) {
        return
    }
    getKeyPressed(key);
})


$("#keyboard-cont").hide()
$(document).ready(() => {
    socket.on("command", (data) => {

        if (typeof (data.command) === "object") {
            if (data.command.command === "drawing_game_init") {
                guessesRemaining = NUMBER_OF_GUESSES;
                currentGuess = [];
                $("#keyboard-cont").show()
                initBoard();
                for (let i=0; i<5; i++) {
                    deleteLetter()
                }

            } else if (data.command.command === "drawing_game_guess") {
//                checkGuess(data.command.guess, data.command.correct_word);
//                submitted = false;
                sendGuess();
            } else if (data.command.command === "unsubmit") {
                // happens when players submit different guesses
                submitted = false;
            }
            switch(data.command.event){

                case "send_instr":
                    $("#text_to_modify").html(data.command.message)
                    break;
                case "send_grid":
                    $("#current-grid").html(data.command.message)
                    break;
            }
        }
    });
});


