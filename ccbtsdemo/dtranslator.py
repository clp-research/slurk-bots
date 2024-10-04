import logging
from .getllmresponse import PromptLLM

class DialogueTranslator:
    def __init__(self, llm_model):
        self.pllm = PromptLLM()
        self.prompt = {}
        self.response = {}
        #self.model = "codellama/CodeLlama-34b-Instruct-hf"#"meta-llama/Meta-Llama-3-8B-Instruct"#
        self.model = llm_model#"gpt-4o"


    def setllmmodel(self, model):
        if model == "model_llm370b":
            model_name = "meta-llama/Meta-Llama-3-70B-Instruct"
        elif model == "model_llm8b":
            model_name = "meta-llama/Meta-Llama-3-8B-Instruct"
        elif model == "model_codellama":
            model_name = "codellama/CodeLlama-34b-Instruct-hf"
        elif model == "model_gpt4o":
            model_name = "gpt-4o"
        logging.info(f"Setting LLM model to {model_name}")
        self.model = model_name

    def reset(self, prompt_type=None):
        if not prompt_type:
            self.prompt = {}
            self.response = {}
            return
        self.prompt[prompt_type] = []
        self.response[prompt_type] = None

    def _cleanup_response(self, response, response_type):
        code_labels = ["Output", "Output:", "Output :", "Output\n", "Output\n:"]
        func_labels = ["Function", "Function:", "Function :", "Function\n", "Function\n:"]
        if response_type == "code":
            labels = code_labels
        elif response_type == "function":
            labels = func_labels

        for label in labels:
            response = response.replace(label, "")
            
        try:
            response = response.strip().split("\n")
            if response:
                if "```python" in response[0]:
                    response[0] = response[0].replace("```python", "").strip()
                    response[-1] = response[-1].replace("```", "").strip()

                if "```" in response[0]:
                    response[0] = response[0].replace("```", "").strip()
                    response[-1] = response[-1].replace("```", "").strip()

                if response[0] in [":", ".", ","]:
                    response = response[1:]

                if response:
                    if response_type == "code":
                        if response[-1] in [":", ".", ","]:
                            response = response[:-1]

                        for resp in response:
                            if not resp:
                                continue
                            if resp[-1] in [":", ".", ","] and ("if" not in resp and "for" not in resp and "while" not in resp and not resp[0].contains("def")):
                                response[response.index(resp)] = resp[:-1]

        except Exception as error:
            logging.error("Error in cleanup_response: ", response, error)

        response = "\n".join(response)
        return response.strip()
    

    def run(self, prompt_type, instruction, skill_name=None, skill_code=None, error=None):

        if prompt_type not in self.prompt:
            self.prompt[prompt_type] = []
            self.response[prompt_type] = None

        reponse_type = None

        if prompt_type == "translate":
            self.pllm.get_prompt(instruction, self.prompt[prompt_type], self.response[prompt_type], error)
            reponse_type = "code"
        elif prompt_type == "repeat-skill":
            self.pllm.repeat_prompt(instruction, skill_name, skill_code, self.prompt[prompt_type], self.response[prompt_type], error)
            reponse_type = "code"
        elif prompt_type == "abstract-skill":
            self.pllm.abstract_prompt(skill_name, skill_code, self.prompt[prompt_type], self.response[prompt_type], error)
            reponse_type = "function"

        model_response = self.pllm.generate(self.model, self.prompt[prompt_type])

        self.response[prompt_type] = self._cleanup_response(model_response, reponse_type)


        logging.debug(f"Prompt Type: {self.prompt[prompt_type]},\nResponse:\n{self.response[prompt_type]}")
        return self.response[prompt_type]

    
if __name__=="__main__":
    dt = DialogueTranslator(None)
    utterance = "fill the grid with red washers"#"place a red washer in the 3rd row, 4th column"
    response = dt.run("translate", utterance)
    print(response)

