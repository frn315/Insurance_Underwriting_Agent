import os
import json
import ssl
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """
    Dumb Transport for LLM (Azure OpenAI).
    No logic. No validation. Just bytes in, bytes out.
    """

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "azure")
        self.api_key = os.getenv("LLM_API_KEY")
        self.endpoint = os.getenv("LLM_AZURE_ENDPOINT")
        self.api_version = os.getenv("LLM_AZURE_API_VERSION")
        self.deployment = os.getenv("LLM_AZURE_DEPLOYMENT")

        # SSL context for macOS certificate issues
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        if not all([self.api_key, self.endpoint, self.api_version, self.deployment]):
            print("[WARN] Azure Config missing. LLM calls may fail.")
            print(f"  API_KEY: {'✓' if self.api_key else '✗'}")
            print(f"  ENDPOINT: {'✓' if self.endpoint else '✗'}")
            print(f"  API_VERSION: {'✓' if self.api_version else '✗'}")
            print(f"  DEPLOYMENT: {'✓' if self.deployment else '✗'}")

    def generate_json(
        self, prompt: str, system_instruction: str = "You are a helpful assistant."
    ) -> Dict[str, Any]:
        """
        Sends prompt to Azure OpenAI and returns JSON response.
        Enforces JSON mode if supported, or relies on prompt instruction.
        """
        if self.provider != "azure":
            raise ValueError(
                "Only 'azure' provider is fully implemented in this phase."
            )

        url = f"{self.endpoint}openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"

        headers = {"Content-Type": "application/json", "api-key": self.api_key}

        payload = {
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},  # Force JSON
            "temperature": 0.0,
            "max_tokens": 800,
        }

        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"), headers=headers
            )
            # Use SSL context to bypass certificate verification
            with urllib.request.urlopen(req, context=self.ssl_context) as response:
                response_body = response.read().decode("utf-8")
                result = json.loads(response_body)

                # Extract content
                content_str = result["choices"][0]["message"]["content"]
                return json.loads(content_str)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            print(f"[LLM Transport] HTTP Error {e.code}: {error_body}")
            raise
        except Exception as e:
            print(f"[LLM Transport] Error: {e}")
            raise
