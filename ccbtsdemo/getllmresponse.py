import string
import requests
import json
from openai import OpenAI
import os
import httpx
import logging
from pathlib import Path
from huggingface_hub import InferenceClient

ROOT = Path(__file__).parent.resolve()


API_URL = "https://api-inference.huggingface.co/models"

RELATED_FILE_PATH = Path(f"{ROOT}")


class PromptLLM:
    def __init__(self):
        with open(f"{RELATED_FILE_PATH}/promptconfig.json", "r") as f:
            self.promptconfig = json.load(f)

        self._set_api_keys()
        self.temperature = self.promptconfig["temperature"]
        self.max_new_tokens = self.promptconfig["max_new_tokens"]
        self.chat_models = self.promptconfig["chat_models"]
        self.openai_models = self.promptconfig["openai_models"]
        # self.hf_headers = {"Authorization": f"Bearer {hf_api_token}"}
        self.hf_headers = {
            "Authorization": f"Bearer {hf_api_token}",
            "Content-Type": "application/json",
        }
        self.openai_client = OpenAI(
            api_key=openai_api_key, organization=openai_organization
        )
        self.genericapi_client = OpenAI(
            base_url=generic_api_url,
            api_key=generic_api_key,
            http_client=httpx.Client(verify=False),
        )

    def _set_api_keys(self):
        global openai_api_key, openai_organization, hf_api_token, generic_api_key, generic_api_url
        # with open("/home/admin/Desktop/codebase/slurk_latest_repo/slurk-bots/ccbts/key.json", "r") as f:
        with open(f"{RELATED_FILE_PATH}/key.json", "r") as f:
            self.keys = json.load(f)
            openai_api_key = self.keys["openai"]["api_key"]
            openai_organization = self.keys["openai"]["organization"]
            hf_api_token = self.keys["huggingface"]["api_key"]
            generic_api_key = self.keys["generic_openai_compatible"]["api_key"]
            generic_api_url = self.keys["generic_openai_compatible"]["base_url"]

    def gettemperature(self):
        return self.temperature

    def settemperature(self, new_temperature):
        self.temperature = new_temperature

    def setmaxtokens(self, max_new_tokens):
        self.max_new_tokens = max_new_tokens

    def _get_prompt_base(self, prompt_type):
        prompt_mapping = {
            "atomic-instruction": "prompt_template_atomic_instruction.txt",
            "repeat-instruction": "prompt_template_repeat_instruction.txt",
            "function-abstraction": "prompt_template_function_abstraction.txt",
            "test-utterances": "prompt_template_gen_test_utterances.template",
            "intent-detection": "prompt_template_intent_detection.txt",
        }

        filename = prompt_mapping.get(prompt_type)
        if not filename:
            raise ValueError(f"Unknown prompt type: {prompt_type}")

        file_path = f"{RELATED_FILE_PATH}/{filename}"

        with open(file_path, "r") as f:
            template = f.read()

        return template

    def _prepare_first_prompt(
        self, template, prompt, instruction=None, skill_code=None
    ):
        if skill_code:
            template = (
                template
                + "\n\n"
                + "Instruction\n"
                + instruction
                + "\n"
                + "Output\n"
                + skill_code
                + "\n"
            )

        elif instruction:
            template = template + "\n\n" + "Instruction\n" + instruction + "\n"

        else:
            template = template + "\n\n"

        prompt.extend([{"role": "user", "content": template}])

    def _add_response(self, prompt, response):
        prompt.extend([{"role": "assistant", "content": response}])

    def _add_followup(self, prompt, error, instruction=None, repeat=False):
        if error:
            prompt.extend(
                [
                    {
                        "role": "user",
                        "content": "Execution Error\n"
                        + error
                        + "\n. Please try again. Dont generate additional explanation\n",
                    }
                ]
            )
        else:
            if repeat:
                if instruction:
                    prompt.extend(
                        [
                            {
                                "role": "user",
                                "content": "Instruction\n" + instruction + "\n",
                            }
                        ]
                    )
            else:
                raise NotImplementedError(
                    "Error handling for multi-turn not implemented yet"
                )

    def get_prompt(self, instruction, prompt=[], response=None, error=None):
        template = self._get_prompt_base("atomic-instruction")
        if not prompt:
            self._prepare_first_prompt(template, prompt, instruction)

        else:
            self._add_response(prompt, response)
            self._add_followup(prompt, error, instruction, True)

    def repeat_prompt(
        self, instruction, combo_name, combo_code, prompt=[], response=None, error=None
    ):
        template = self._get_prompt_base("repeat-instruction")
        template = string.Template(template).safe_substitute(
            **({"COMBO_NAME": combo_name, "COMBO_CODE": combo_code})
        )

        if not prompt:
            self._prepare_first_prompt(template, prompt, instruction)

        else:
            self._add_response(prompt, response)
            self._add_followup(prompt, error, instruction)

    def abstract_prompt(
        self, skill_instruction, skill_code, prompt=[], response=None, error=None
    ):
        template = self._get_prompt_base("function-abstraction")

        if not prompt:
            self._prepare_first_prompt(template, prompt, skill_instruction, skill_code)

        else:
            self._add_response(prompt, response)
            # If multiple turns are supported, skill_code also needs to be passed
            self._add_followup(prompt, error, skill_instruction)

    def testutterance_prompt(
        self, intent_type, examples, prompt=[], response=None, error=None
    ):
        template = self._get_prompt_base("test-utterances")
        template = string.Template(template).safe_substitute(
            **({"INTENT_TYPE": intent_type, "EXAMPLE_UTTERANCES": examples})
        )

        if not prompt:
            self._prepare_first_prompt(template, prompt)

        else:
            self._add_response(prompt, response)
            self._add_followup(prompt, error)

    def get_intent_prompt(self, instruction, prompt=[], response=None, error=None):
        template = self._get_prompt_base("intent-detection")

        if not prompt:
            self._prepare_first_prompt(template, prompt, instruction)

        else:
            self._add_response(prompt, response)
            if not error:
                self._add_followup(prompt, error, instruction, True)

    def generate(self, model, prompt):
        logging.debug(f"Testing model {model} with temperature {self.temperature}")
        if model in self.openai_models:
            return self.call_openai(model, prompt)

        else:
            #return self.call_hfapi(model, prompt)
            return self.call_genericapi(model, prompt)

    def call_openai(self, model, prompt):
        # client = OpenAI(api_key=openai_api_key, organization=openai_organization)

        if model in self.chat_models:
            api_response = self.openai_client.chat.completions.create(
                model=model,
                messages=prompt,
                temperature=self.temperature,
                max_tokens=self.max_new_tokens,
            )
            response = api_response.choices[0].message
            if response.role != "assistant":  # safety check
                raise AttributeError(
                    "Response message role is "
                    + response.role
                    + " but should be 'assistant'"
                )
            response = response.content.strip()

        else:
            prompt = "\n".join([message["content"] for message in prompt])

            api_response = self.openai_client.completions.create(
                model=model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_new_tokens,
            )

            response = api_response.choices[0].text.strip()

        return response

    def call_hfapi(self, model, prompt_text):
        client = InferenceClient(
            model,
            token=hf_api_token,
        )

        response = client.chat_completion(messages=prompt_text, max_tokens=self.max_new_tokens)

        return response.choices[0]["message"]["content"].strip()

    def call_genericapi(self, model, messages):
        if model.startswith("fsc-") or model.startswith("lcp-"):
            model = model[4:]

        prompt_text = messages
        model_parameters = {
                "temperature": self.temperature,
                "max_tokens": self.max_new_tokens
            }

      
        api_response = self.genericapi_client.chat.completions.create(
            model=model, messages=prompt_text, **model_parameters
        )

        response = api_response.choices[0].message
        if response.role != "assistant":  # safety check
            raise AttributeError(
                "Response message role is "
                + response.role
                + " but should be 'assistant'"
            )
        response = response.content.strip()

        return response

if __name__ == "__main__":
    promptllm = PromptLLM()

    prompt = []
    test_data = "place red bridge horizontally at 1st row 3rd column"
    promptllm.get_prompt(test_data, prompt)

    #generated_code = promptllm.generate("codellama/CodeLlama-34b-Instruct-hf", prompt)
    generated_code = promptllm.generate("llama-3.1-8b-instant", prompt)
    print(generated_code)
