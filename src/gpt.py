import logging
import os
from typing import Dict, List, Tuple

from openai import OpenAI

log = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def set_openai_key():
    if client.api_key is None:
        log.warning("OpenAI API key not found.")
    else:
        log.info("OpenAI API key set.")


def gpt_text(
    messages: List[Dict[str, str]] = None,
    model="gpt-3.5-turbo",
    temperature: float = 0,
    max_tokens: int = 32,
    stop: List[str] = ["\n"],
) -> str:
    log.debug(f"Sending messages to OpenAI: {messages}")
    response = client.chat_completions.create(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop=stop,
    )
    reply: str = response.choices[0].message.content
    log.debug(f"Received reply from OpenAI: {reply}")
    return reply


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    set_openai_key()
    print(gpt_text(max_tokens=8, messages=[{"role": "user", "content": "hello"}]))