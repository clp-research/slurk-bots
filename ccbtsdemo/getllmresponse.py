import requests
import json
from openai import OpenAI
import os
import httpx

from pathlib import Path


ROOT = Path(__file__).parent.resolve()


API_URL = "https://api-inference.huggingface.co/models/"

RELATED_FILE_PATH = Path(
    f"{ROOT}"
)


class PromptLLM:
    def __init__(self):
        print(os.getcwd())
        #with open("/home/admin/Desktop/codebase/slurk_latest_repo/slurk-bots/ccbts/promptconfig.json", "r") as f:
        with open(f"{RELATED_FILE_PATH}/promptconfig.json", "r") as f:
            self.promptconfig = json.load(f)

        self._set_api_keys()
        self.temperature = self.promptconfig["temperature"]
        self.max_new_tokens = self.promptconfig["max_new_tokens"]
        self.chat_models = self.promptconfig["chat_models"]
        self.openai_models = self.promptconfig["openai_models"]
        #self.hf_headers = {"Authorization": f"Bearer {hf_api_token}"}
        self.hf_headers = {"Authorization": f"Bearer {hf_api_token}", "Content-Type": "application/json"}
        self.openai_client = OpenAI(api_key=openai_api_key, organization=openai_organization)
        self.genericapi_client = OpenAI(base_url=generic_api_url, api_key=generic_api_key, http_client=httpx.Client(verify=False))


    def _set_api_keys(self):
        global openai_api_key, openai_organization, hf_api_token, generic_api_key, generic_api_url
        #with open("/home/admin/Desktop/codebase/slurk_latest_repo/slurk-bots/ccbts/key.json", "r") as f:
        with open(f"{RELATED_FILE_PATH}/key.json", "r") as f:
            self.keys = json.load(f)
            openai_api_key = self.keys["openai"]["api_key"]
            openai_organization = self.keys["openai"]["organization"]
            hf_api_token = self.keys["huggingface"]["api_key"]
            generic_api_key = self.keys["generic_openai_compatible"]["api_key"]
            generic_api_url = self.keys["generic_openai_compatible"]["base_url"]

    def get_prompt(self, test_data, prompt=[], response=None):
        #with open("/home/admin/Desktop/codebase/slurk_latest_repo/slurk-bots/ccbts/prompt_template_atomic_instruction.txt", "r") as f:
        with open(f"{RELATED_FILE_PATH}/prompt_template_atomic_instruction.txt", "r") as f:            
            template = f.read()

        if not prompt:
            template = template + "\n\n" + "Instruction\n" + test_data + "\n"
            prompt.extend([{"role": "user", "content": template}])

        else:
            prompt.extend([{"role": "assistant", "content": response}])
            prompt.extend(
                [{"role": "user", "content": "Instruction\n" + test_data + "\n"}]
            )

    def generate(self, model, prompt):
        # print(f"Testing model {model} with temperature {self.temperature}")
        if model in self.openai_models:
            return self.call_openai(model, prompt)
        else:
            #return self.call_hfapi(model, prompt)
            return self.call_genericapi(model, prompt)

    def call_openai(self, model, prompt):
        #client = OpenAI(api_key=openai_api_key, organization=openai_organization)

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
    
    def _prepare_data_open_models(self, model, messages):
        model_types = {
            "llama__models": [
                "codellama/CodeLlama-34b-Instruct-hf",
                "codellama/CodeLlama-70b-Instruct-hf",
                "mistralai/Mistral-7B-Instruct-v0.1",
                "codellama-34b-instruct"
            ],
            "nonllama_models": [
                "tiiuae/falcon-7b-instruct",
                "Salesforce/codegen-350M-mono",
                "Salesforce/codet5p-220m",
                "Salesforce/codet5p-770m",
                "Salesforce/codet5p-220m-py",
                "Salesforce/codet5p-770m-py",
                "bigcode/starcoderbase-1b",
                "bigcode/starcoder",
            ],
        }
        if not self.promptconfig["use_hf_api_local"]:
            if model in model_types["llama__models"]:
                prompt_text = (
                    "".join(
                        [
                            f'[/INS] {m["content"]}.'
                            if m["role"] == "assistant"
                            else f'<s> [INS] {m["content"]}'
                            for m in messages
                        ]
                    )
                    + "[/INS]"
                )
            elif model in model_types["nonllama_models"]:
                prompt_text = "\n".join([m["content"] for m in messages])
            else:
                prompt_text = messages
        else:
            prompt_text = messages

        self.temperature = self.temperature or 0.01
        if "hf" in model or model in model_types["nonllama_models"]:
            model_parameters = {
                "temperature": self.temperature,
                "max_new_tokens": self.max_new_tokens,
                "num_return_sequences": 1,
            }
        else:
            model_parameters = {
                "temperature": self.temperature,
                "max_tokens": self.max_new_tokens
            }

        return prompt_text, model_parameters

    def call_hfapi(self, model, messages):

        prompt_text, model_parameters = self._prepare_data_open_models(model, messages)

        if not self.promptconfig["use_hf_api_local"]:
            model_url = f"{API_URL}{model}"
            #model_url = f"{API_URL}"

            payload = {"inputs": prompt_text, "parameters": model_parameters}

            try:
                with requests.post(
                    model_url, headers=self.hf_headers, json=payload
                ) as response:
                    print(response)
                    response_data = response.json()
                    if "error" in response_data:
                        return response_data["error"]
                    

                    text = response_data[0]["generated_text"]
                    return (
                        text.replace(prompt_text, "").strip()
                        if prompt_text in text
                        else text
                    )
            except requests.RequestException as e:
                return f"Request failed: {e}"
        else:
            return self.prompthflocal.generate(model, model_parameters, prompt_text)

    def call_genericapi(self, model, messages):

        if model.startswith('fsc-') or model.startswith('lcp-'):
            model = model[4:] 

        prompt_text, model_parameters = self._prepare_data_open_models(model, messages)

        api_response = self.genericapi_client.chat.completions.create(model=model, messages=prompt_text,
                                                         **model_parameters)

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

    generated_code = promptllm.generate("codellama/CodeLlama-34b-Instruct-hf", prompt)
    print(generated_code)