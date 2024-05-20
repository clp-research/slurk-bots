
from .rasahandler import RasaHandler


class DADetector:
    def __init__(self):
        self.rhandler = RasaHandler()


    def run(self, utterance):
        daresponse = {"utterance": utterance}
        if "undo" in utterance.lower():
            daresponse["dialogue_act"] = "UNDO"
        else:
            return self.rhandler.parse(utterance)

        return daresponse