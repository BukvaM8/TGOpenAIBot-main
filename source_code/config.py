from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TG_BOT_TOKEN")
NGROK_URL = os.getenv("NGROK_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
OPEN_AI_KEY = os.getenv("OPENAI_TOKEN")
CHATGPT_MODEL = os.getenv("CHATGPT_MODEL")
OPERATOR_CHAT_ID = int(os.getenv("OPERATOR_CHAT_ID"))
