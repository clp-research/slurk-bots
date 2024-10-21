const NUMBER_OF_GUESSES = 6;
let guessesRemaining = NUMBER_OF_GUESSES;
let currentGuess = [];
let nextLetter = 0;
let submitted = false;  // whether a guess was submitted


function initBoard() {
    let board = document.getElementById("game-board");
    board.textContent = "";

    for (let i = 0; i < NUMBER_OF_GUESSES; i++) {
        let row = document.createElement("div")
        row.className = "letter-row"

        for (let j = 0; j < 5; j++) {
            let box = document.createElement("div")
            box.className = "letter-box"
            row.appendChild(box)
        }
        board.appendChild(row)
    }
    for (const elem of document.getElementsByClassName("keyboard-button")) {
    elem.style.backgroundColor = "";
}

}


function shadeKeyBoard(letter, color) {
    for (const elem of document.getElementsByClassName("keyboard-button")) {
        if (elem.textContent.trim() === letter) {
            let oldColor = elem.style.backgroundColor
            if (oldColor === 'green') {
                return
            }

            if (oldColor === 'yellow' && color !== 'green') {
                return
            }

            elem.style.backgroundColor = color
            break
        }
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


function showGuess(guessString, colors) {
    let row = document.getElementsByClassName("letter-row")[6 - guessesRemaining]

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
            shadeKeyBoard(guessString[i], colors[i])
        }, delay)
    }
    // update game variables
    guessesRemaining -= 1;
    currentGuess = [];
    nextLetter = 0;
}


function insertLetter(pressedKey) {
    if (nextLetter === 5) {
        return
    }
    pressedKey = pressedKey.toLowerCase()

    let row = document.getElementsByClassName("letter-row")[6 - guessesRemaining]
    let box = row.children[nextLetter]
    animateCSS(box, "pulse")
    box.textContent = pressedKey
    box.classList.add("filled-box")
    currentGuess.push(pressedKey)
    nextLetter += 1
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
    let guessString = ''

    for (const val of currentGuess) {
        guessString += val
    }

    socket.emit("message_command",
        {
            "command": {
                "guess": guessString,
                "remaining": guessesRemaining
            },
            "room": self_room
        }
    )
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
            if (data.command.command === "wordle_init") {
                guessesRemaining = NUMBER_OF_GUESSES;
                currentGuess = [];
                 $("#keyboard-cont").show()
                initBoard();
                for (let i=0; i<5; i++) {
                    deleteLetter()
                }

            } else if (data.command.command === "wordle_guess") {
                showGuess(data.command.guess, data.command.colors);
                submitted = false;
            } else if (data.command.command === "unsubmit") {
                // happens when players submit different guesses
                submitted = false;
            }
            else if (data.command.command === "wordle_init_critic") {
                guessesRemaining = NUMBER_OF_GUESSES;
                currentGuess = [];
                initBoard();
                for (let i=0; i<5; i++) {
                    deleteLetter()
                }
                 }
            switch(data.command.event){

                case "send_instr":
                    $("#text_to_modify").html(data.command.message)
                    break;
            }



//

        }
    });
});

function confirm_ready(answer){
    socket.emit("message_command",
        {
            "command": {
                "event": "confirm_ready",
                "answer": answer
            },
            "room": self_room
        }
    )
}

function critic_feedback(answer){
    socket.emit("message_command",
        {
            "command": {
                "event": "critic_feedback",
                "answer": answer
            },
            "room": self_room
        }
    )
}
