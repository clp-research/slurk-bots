from .rasahandler import RasaHandler

class ResponseGenerator:
    def __init__(self):
        self.rhandler = RasaHandler()

    def handleerror(self, error):
        return "Sorry, I don't understand. Can you please repeat?"
    
    def generate(self, utterance):
        return self.rhandler.generate(utterance)