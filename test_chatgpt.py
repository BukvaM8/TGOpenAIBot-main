import openai
from source_code.config import OPEN_AI_KEY, CHATGPT_MODEL
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chatgpt_interaction():
    openai.api_key = OPEN_AI_KEY
    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]

    try:
        response = openai.ChatCompletion.create(
            model=CHATGPT_MODEL,
            messages=messages
        )

        reply = response['choices'][0]['message']['content']
        logger.info(f"ChatGPT response: {reply}")
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {str(e)}")

if __name__ == "__main__":
    test_chatgpt_interaction()
