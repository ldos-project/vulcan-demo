import re
from openai import OpenAI

AVAILABLE_MODELS = ["claude-sonnet", "claude-opus"]
DEFAULT_MODEL = "claude-sonnet"

class LLM:
    def __init__(self, model: str = DEFAULT_MODEL, system: str = None):
        self.client = OpenAI(
            base_url="https://workshop.dwivedula.dev/v1",
            api_key="sk-<<add sk here>>",
        )
        self.model = model
        self.messages = []
        if system:
            self.messages.append({"role": "system", "content": system})

    def send(self, message: str, temperature: float = 1.0) -> dict:
        self.messages.append({"role": "user", "content": message})
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=temperature,
        )
        text = resp.choices[0].message.content
        self.messages.append({"role": "assistant", "content": text})
        code_blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.DOTALL)
        return {
            "full_response": text,
            "code": code_blocks[-1].strip() if code_blocks else text.strip(),
            "usage": {
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else None,
                "gen_tokens": resp.usage.completion_tokens if resp.usage else None,
            },
        }

    def reset(self):
        system = self.messages[0] if self.messages and self.messages[0]["role"] == "system" else None
        self.messages = [system] if system else []
