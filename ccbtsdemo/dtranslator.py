import logging
from .getllmresponse import PromptLLM

class DialogueTranslator:
    def __init__(self):
        self.pllm = PromptLLM()
        self.prompt = []
        self.response = None
        self.model = "codellama/CodeLlama-34b-Instruct-hf"#"meta-llama/Meta-Llama-3-8B-Instruct"#
        #self.model = "gpt-4o"

    def reset(self):
        self.prompt = []
        self.response = None


    def _cleanup_response(self, response):
        logging.debug(f"Response before cleanup: {response}")
        labels = ["Output", "Output:", "Output :", "Output\n", "Output\n:"]
        for label in labels:
            response = response.replace(label, "")
            
        try:
            response = response.strip().split("\n")
            if response:
                if response[0] in [":", ".", ","]:
                    response = response[1:]

                if response:
                    if response[-1] in [":", ".", ","]:
                        response = response[:-1]

                for resp in response:
                    if resp[-1] in [":", ".", ","]:
                        response[response.index(resp)] = resp[:-1]
        except Exception as error:
            logging.error(f"Error in cleanup_response: response: {response}, error: {error}")
        
        response = "\n".join(response)
        return response


    def run(self, utterance, error=None):
        self.pllm.get_prompt(utterance, self.prompt, self.response, error)

        self.response = self.pllm.generate(self.model, self.prompt)

        logging.debug(f"Response from LLM: {self.response}")

        self.response = self._cleanup_response(self.response)

        return self.response
    
if __name__=="__main__":
    dt = DialogueTranslator()
    utterance = "place a red washer in the 3rd row, 4th column"
    response = dt.run(utterance)
    print(response)