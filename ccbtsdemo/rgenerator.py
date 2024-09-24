
class ResponseGenerator:
    def __init__(self, rasa_handler):
        self.rhandler = rasa_handler

    def handleerror(self, error=None):
        # TODO: Generate message based on error type
        return "Sorry, I don't understand. Can you please repeat?"
    
    def generate(self, utterance, previntent = None):
        return self.rhandler.generate(utterance, previntent)
