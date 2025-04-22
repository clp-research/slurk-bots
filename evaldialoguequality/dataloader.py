import logging
import json


from pathlib import Path



ROOT = Path(__file__).parent.resolve()
RELATED_IMAGE_PATH = Path(
    f"{ROOT}/data/"
)


class Dataloader:
    def __init__(self):
        self.dialogues = self.loaddialogues()
        self.dialogue_for_eval = self._get_generator()   
        self.current_progress = self.load_progress()
        self.remaining_dialogues = [
            d for d in self.dialogues if d not in self.current_progress
        ]

    def loaddialogues(self):
        try:
            with open(f"{ROOT}/data/eval_dialogues.json", "r") as file:
                eval_data = json.load(file)
                logging.debug(f"Loaded Dialogues: {len(eval_data)}")
                return eval_data
        except FileNotFoundError:
            logging.debug("eval_dialogues.json is not available, returning empty dict")
            return {}        
        
    def _get_generator(self):
        """
        Internal generator that yields dialogues one by one.
        """
        for dialogue_id in self.remaining_dialogues:
            yield dialogue_id, self.dialogues[dialogue_id]

    def load_progress(self) :
        # Load progress
        try:
            with open(f"{ROOT}/data/eval_progress.json", "r") as file:        
                completed_ids = set(json.load(file))
        except Exception as error:
            logging.debug(f"eval_progress.json is not available {error}, returning empty set")
            completed_ids = set()

        return completed_ids
    
    def _save_progress(self, completed_ids):
        # Save progress
        with open(f"{ROOT}/data/eval_progress.json", "w") as file:
            json.dump(list(completed_ids), file)
            logging.debug(f"Saved progress: {completed_ids}")

    def mark_as_completed(self, dialogue_id):
        """
        Marks a dialogue as completed.
        """
        self.current_progress.add(dialogue_id)
        self._save_progress(self.current_progress)
        logging.debug(f"Marked dialogue {dialogue_id} as completed.")

    def get_next_dialogue(self):
        """
        Returns the next dialogue dict, or None if all are exhausted.
        """
        try:
            dialogue_id, dialogue = next(self.dialogue_for_eval)
            # Do not mark the dialogue as completed - Let the main file do it, as user may quit the room after loading the dialogue
            #self.current_progress.add(dialogue_id)
            #self.save_progress(self.current_progress)
            return dialogue_id, dialogue
        except StopIteration:
            return None, None
        
if __name__ == "__main__":
    dl = Dataloader()
    print(dl.get_next_dialogue())
