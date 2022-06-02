const NUMBER_OF_GUESSES = 6;
let guessesRemaining = NUMBER_OF_GUESSES;
let currentGuess = [];
let nextLetter = 0;
let rightGuessString = "";


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
}


function shadeKeyBoard(letter, color) {
    for (const elem of document.getElementsByClassName("keyboard-button")) {
        if (elem.textContent === letter) {
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


function deleteLetter () {
    let row = document.getElementsByClassName("letter-row")[6 - guessesRemaining]
    let box = row.children[nextLetter - 1]
    box.textContent = ""
    box.classList.remove("filled-box")
    currentGuess.pop()
    nextLetter -= 1
}


function checkGuess (guessString) {
    let row = document.getElementsByClassName("letter-row")[6 - guessesRemaining]
    let rightGuess = Array.from(rightGuessString)


    let colors = ["", "", "", "", ""];
	let remaining = Array.from(rightGuessString)

    // first check for green letters
    for (let i=0; i<5; i++){
      	let guessLetter = guessString.charAt(i);
      	let solutionLetter = rightGuess[i];
      	if (guessLetter === solutionLetter){
      		colors[i] = "green";
      		remaining[i] = " ";
      	}
    }
 
    // check for yellows and greys
    for (let i = 0; i < 5; i++) {
	    let guessLetter = guessString.charAt(i);

		if (remaining.includes(guessLetter) === true){
		    if (colors[i] === ""){
		  		colors[i] = "yellow";
		  	}
		} else {
		    if (colors[i] === ""){
		  		colors[i] = "grey";
		  	}
	    }  
    }

    for (let i = 0; i < 5; i++) {
  	    let box = row.children[i]
        console.log(box)
        let delay = 250 * i
        setTimeout(()=> {
            // flip box
            animateCSS(box, 'flipInX')
            // shade box
            box.style.backgroundColor = colors[i]
            // prevent user's shenanigans
            box.textContent = guessString[i]
            shadeKeyBoard(guessString[i], colors[i])
        }, delay)
    }

    // // users won
    // if (guessString === rightGuessString) {
    //     socket.emit("message_command", 
    //         {"command": "end_round won", "room": self_room}
    //     );
    //     guessesRemaining = 0;
    //     return

    // } else {
    //     guessesRemaining -= 1;
    //     currentGuess = [];
    //     nextLetter = 0;

    //     if (guessesRemaining === 0) {
    //         socket.emit("message_command", 
    //             {"command": "end_round lost", "room": self_room}
    //         );
    //     }
    // }
}


function insertLetter (pressedKey) {
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

    node.addEventListener('animationend', handleAnimationEnd, {once: true});
});


function sendGuess() {
    let guessString = ''

    for (const val of currentGuess) {
        guessString += val
    }
    
    console.log(guessString)
    console.log(self_room)
    socket.emit("message_command", 
        {"command": "guess " + guessString + " " + guessesRemaining, "room": self_room}
    )
}


function getKeyPressed(letter) {
    if (guessesRemaining === 0) {
        return
    }

    let pressedKey = String(letter)

    if (pressedKey === "DEL" && nextLetter !== 0) {
        deleteLetter()
        return
    }

    if (pressedKey === "ENTER") {
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
    // console.log("emitting")
    // console.log(e.originalTarget.innerText)
    
    
    socket.emit("text_message", key);     
    if (!target.classList.contains("keyboard-button")) {
        return
    }

    getKeyPressed(key);
})


$("#keyboard-cont").hide()
$(document).ready(() => {
    socket.on("command", (data) => {
        console.log(data)

        var command = data.command
        if (command.includes("wordle_init")){
            rightGuessString = command.split(" ")[1];
            guessesRemaining = NUMBER_OF_GUESSES;
            currentGuess = [];
            $("#keyboard-cont").show()
            initBoard();
            for (let i = 0; i < 5; i++) {
                deleteLetter()
            }

        } else if (command.includes("wordle_guess")){
            userInput = command.split(" ")[1];
            checkGuess(userInput);
        }
        
    });
});
