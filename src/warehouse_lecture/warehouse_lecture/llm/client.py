"""OpenAI client wrapper: config-driven models, retries, structured output, usage log.

Every lecture example talks to OpenAI through this module so that model names,
temperature and cost bookkeeping live in one place (config/llm.yaml + .env).
"""

import base64
from dataclasses import dataclass
import datetime as dt
import io
import json
import os
from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory


def _find_workspace():
    here = Path.cwd()
    for candidate in (here, *here.parents):
        if (candidate / "src" / "warehouse_lecture").is_dir():
            return candidate
    return here


def load_config(path=None):
    file = Path(path) if path else Path(get_package_share_directory("warehouse_lecture")) / "config/llm.yaml"
    return yaml.safe_load(file.read_text())


def load_env():
    """Load OPENAI_API_KEY from the workspace .env without overriding a real env var."""
    from dotenv import load_dotenv

    for candidate in (_find_workspace() / ".env", Path.cwd() / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            break
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set; copy .env.example to .env and fill in the key")


@dataclass
class Usage:
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    purpose: str


class LLM:
    def __init__(self, config=None, *, usage_log=None):
        from openai import OpenAI

        load_env()
        self.config = config or load_config()
        d = self.config["defaults"]
        self.client = OpenAI(timeout=d.get("timeout_s", 30), max_retries=d.get("max_retries", 2))
        self.models = self.config["models"]
        self.pricing = self.config.get("pricing", {})
        self.log_path = Path(usage_log or _find_workspace() / self.config.get("usage_log", "logs/openai_usage.jsonl"))
        self.session_cost = 0.0

    # --- bookkeeping ----------------------------------------------------
    def _record(self, model, usage, purpose):
        if usage is None:
            return None
        inp = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", 0) or 0
        out = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", 0) or 0
        price = self.pricing.get(model, {"input": 0.0, "output": 0.0})
        cost = inp / 1e6 * price["input"] + out / 1e6 * price["output"]
        self.session_cost += cost
        entry = Usage(model, inp, out, cost, purpose)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a") as f:
            f.write(json.dumps({"time": dt.datetime.now().isoformat(timespec="seconds"), **entry.__dict__}) + "\n")
        return entry

    # --- text -----------------------------------------------------------
    def chat(self, messages, *, model=None, temperature=None, max_tokens=None, purpose="chat", **kwargs):
        """Plain text completion. messages: [{"role": ..., "content": ...}, ...]."""
        model = model or self.models["chat"]
        d = self.config["defaults"]
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=d["temperature"] if temperature is None else temperature,
            max_tokens=max_tokens or d["max_output_tokens"],
            **kwargs,
        )
        self._record(model, response.usage, purpose)
        return response.choices[0].message.content

    def parse(self, messages, schema, *, model=None, temperature=None, purpose="parse"):
        """Structured output: returns an instance of the pydantic ``schema``."""
        model = model or self.models["chat"]
        d = self.config["defaults"]
        response = self.client.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=schema,
            temperature=d["temperature"] if temperature is None else temperature,
            max_tokens=d["max_output_tokens"],
        )
        self._record(model, response.usage, purpose)
        message = response.choices[0].message
        if message.refusal:
            raise ValueError(f"Model refused: {message.refusal}")
        return message.parsed

    def tools(self, messages, tools, *, model=None, temperature=None, purpose="tools", tool_choice="auto"):
        """One tool-calling round. Returns (assistant_message, [(name, args_dict, call_id), ...])."""
        model = model or self.models["chat"]
        d = self.config["defaults"]
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=d["temperature"] if temperature is None else temperature,
            max_tokens=d["max_output_tokens"],
        )
        self._record(model, response.usage, purpose)
        message = response.choices[0].message
        calls = [
            (c.function.name, json.loads(c.function.arguments or "{}"), c.id)
            for c in (message.tool_calls or [])
        ]
        return message, calls

    # --- vision ---------------------------------------------------------
    @staticmethod
    def image_content(rgb, *, detail="low", fmt="JPEG", quality=85):
        """Encode an RGB uint8 array as an image content part for chat messages."""
        from PIL import Image

        buffer = io.BytesIO()
        Image.fromarray(rgb).save(buffer, format=fmt, quality=quality)
        data = base64.b64encode(buffer.getvalue()).decode()
        mime = "image/jpeg" if fmt.upper() == "JPEG" else "image/png"
        return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}", "detail": detail}}

    def describe_image(self, rgb, prompt, *, model=None, purpose="vision", detail="low"):
        model = model or self.models["vision"]
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}, self.image_content(rgb, detail=detail)]}]
        return self.chat(messages, model=model, purpose=purpose)

    def parse_image(self, rgb, prompt, schema, *, model=None, purpose="vision_parse", detail="low"):
        model = model or self.models["vision"]
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}, self.image_content(rgb, detail=detail)]}]
        return self.parse(messages, schema, model=model, purpose=purpose)


def tool_schema(name, description, parameters, required=None):
    """Helper to build one OpenAI function tool definition from a JSON-schema properties dict."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required or list(parameters),
                "additionalProperties": False,
            },
        },
    }
