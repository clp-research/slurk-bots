function validateForm() {
    const fieldsets = document.querySelectorAll('fieldset');
    let isValid = true;

    fieldsets.forEach((fieldset, index) => {
        const radioButtons = fieldset.querySelectorAll('input[type="radio"]');
        const errorMessageSpan = fieldset.querySelector('.error-message');
        const isChecked = Array.from(radioButtons).some(button => button.checked);

        // Clear any previous error message.
        errorMessageSpan.textContent = '';

        // If none of the radio buttons are checked, display an error message
        if (!isChecked) {
            errorMessageSpan.textContent = 'Please answer this question.';
            isValid = false;
        }
        // Check if 'Other' is selected and the corresponding text box is empty
        const otherRadioButton = fieldset.querySelector('input[type="radio"][value="6"]');
        if (otherRadioButton && otherRadioButton.checked) {
            const otherTextbox = fieldset.querySelector('input[name="player_rating_other"]');
            console.log(otherTextbox.value.trim())

            if (!otherTextbox.value.trim()) {
                errorMessageSpan.textContent = 'Please specify the reason';
                isValid = false;
            }
        }		    
    });

    return isValid;
}

function get_answers(){
    let answers = {}

    const fieldsets = document.querySelectorAll('fieldset');
    fieldsets.forEach((fieldset, index) => {
        const radioButtons = fieldset.querySelectorAll('input[type="radio"]');

        let question = fieldset.children[0].firstChild.nodeValue
        

        nodes = Array.from(radioButtons)
        nodes.forEach((element) => {
            console.log(element)
            if (element.checked){
                answers[question] = element.value
            }
        })


        const otherRadioButton = fieldset.querySelector('input[type="radio"][value="6"]');
        if (otherRadioButton && otherRadioButton.checked) {
            const otherTextbox = fieldset.querySelector('input[name="player_rating_other"]');
            if (otherTextbox.value.trim()) {
                answers[question] = otherTextbox.value.trim()
            }
        }	
    });

    return answers
}