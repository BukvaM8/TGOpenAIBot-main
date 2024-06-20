import logging
from config import NGROK_URL, TOKEN, OPERATOR_CHAT_ID
from models import *
from db import *
from fastapi import FastAPI, Request, HTTPException, Depends
import aiohttp
from redis_client import redis
from chatgpt import ChatGPT
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
openai = ChatGPT()

webhook_url = f"{NGROK_URL}/webhook/"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

set_webhook_url = f"{BASE_URL}/setWebhook?url="
delete_webhook_url = f"{BASE_URL}/deleteWebhook"

async def manage_webhooks(delete_webhook_url, set_webhook_url, webhook_url):
    logger.info("Managing webhooks")
    async with aiohttp.ClientSession() as session:
        async with session.get(delete_webhook_url) as response:
            if response.status == 200:
                logger.info("Webhook deleted successfully")
            else:
                logger.error(f"Failed to delete webhook: {response.status}")
                return

        async with session.get(set_webhook_url + webhook_url) as response:
            if response.status == 200:
                logger.info("Webhook set successfully")
            else:
                logger.error(f"Failed to set webhook: {response.status}")
                return

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up")
    await asyncio.sleep(10)  # Добавьте задержку
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await manage_webhooks(delete_webhook_url, set_webhook_url, webhook_url)

async def get_redis_status(chat_id: int):
    logger.info(f"Fetching Redis status for chat_id: {chat_id}")
    chat_status = await redis.get(chat_id) or "bot"
    return chat_status  # Redis returns a string, no need to decode

async def send_message_to_chat(text: str, chat_id: int, keyboard=True):
    logger.info(f"Sending message to chat_id: {chat_id}")
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }

    if keyboard:
        chat_status = await get_redis_status(chat_id)
        if chat_status == "operator":
            button_text = "Отсоединить оператора"
        else:
            button_text = "Подключить оператора"

        payload["reply_markup"] = {
            "keyboard": [[{"text": button_text}]],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }

    logger.info(f"Request payload: {payload}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response text: {response_text}")
                if response.status != 200:
                    logger.error(f"Failed to send message. Status code: {response.status}")
                    logger.error(f"Response text: {response_text}")
                else:
                    logger.info("Message sent successfully")
                    logger.info(text)
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")

async def send_minimal_message_to_chat(text: str, chat_id: int):
    logger.info(f"Sending minimal message to chat_id: {chat_id}")
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    
    logger.info(f"Minimal request payload: {payload}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as response:
                response_text = await response.text()
                logger.info(f"Minimal response status: {response.status}")
                logger.info(f"Minimal response text: {response_text}")
                if response.status != 200:
                    logger.error(f"Failed to send minimal message. Status code: {response.status}")
                    logger.error(f"Minimal response text: {response_text}")
                else:
                    logger.info("Minimal message sent successfully")
                    logger.info(text)
        except Exception as e:
            logger.error(f"Exception occurred in minimal message: {str(e)}")

async def process_openai_message(text: str, chat_id: int):
    logger.info(f"Processing OpenAI message for chat_id: {chat_id}")
    logger.info(f"Sending to OpenAI: {text}")  # Логирование отправляемого сообщения
    try:
        await openai.send_message(text)
        response = await openai.get_response()
        logger.info(f"Received from OpenAI: {response}")  # Логирование полученного ответа
        await send_minimal_message_to_chat(response, chat_id=chat_id)
    except Exception as e:
        error_message = f"Проблема соединения с ChatGPT. Код ошибки: {e.__class__.__name__} - {str(e)}.\nСвяжитесь с оператором."
        logger.error(f"Error sending message to OpenAI: {str(e)}")
        await send_minimal_message_to_chat(error_message, chat_id)

async def handle_operator_message(message):
    logger.info(f"Handling operator message: {message}")
    try:
        client_id, reply = message.split(':', 1)
        await send_minimal_message_to_chat(f"Ответ оператора: {reply.strip()}", client_id.strip())
    except ValueError:
        await send_minimal_message_to_chat("Неверный формат сообщения. Используйте формат 'chat_id: сообщение'.", OPERATOR_CHAT_ID)

@app.post("/webhook/")
async def webhook(req: Request, db: AsyncSession = Depends(get_db)):
    logger.info("Received webhook event")
    try:
        data = await req.json()
        logger.info(f"Webhook data: {data}")
        chat_id = data['message']['chat']['id']
        text = data['message']['text'].strip().lower()

        if text == "/start":
            welcome_message = f"Привет! Я ваш новый бот. Задайте мне любой вопрос и я отвечу. Нажмите кнопку для связи с оператором. Ваш номер чата {chat_id}"
            await send_message_to_chat(welcome_message, chat_id)
            await redis.set(chat_id, "bot")
            return

        dialogue_query = await db.execute(select(Dialogue).filter_by(chat_id=str(chat_id)))
        dialogue = dialogue_query.scalars().first()

        if not dialogue:
            dialogue = Dialogue(chat_id=str(chat_id))
            db.add(dialogue)
            await db.commit()
            await db.refresh(dialogue)

        message = Message(text=text, dialogue_id=dialogue.id)
        db.add(message)
        await db.commit()

        if chat_id == OPERATOR_CHAT_ID:
            await handle_operator_message(text)
            return

        chat_status = await get_redis_status(chat_id)

        logger.info(f"Chat status for chat_id {chat_id}: {chat_status}")

        if text == 'подключить оператора':
            await send_minimal_message_to_chat("Подключаю оператора...", chat_id)
            await redis.set(chat_id, "operator")
            await send_message_to_chat(f"Сообщение от пользователя {chat_id}.\nОтветьте в формате id: сообщение", OPERATOR_CHAT_ID, keyboard=False)
            await send_message_to_chat("Оператор подключен. Можете отправлять сообщения.", chat_id)

        elif text == 'отсоединить оператора':
            await send_minimal_message_to_chat("Отсоединяю оператора...", chat_id)
            await redis.set(chat_id, "bot")
            await send_message_to_chat(f"Пользователь {chat_id} отсоединил оператора", OPERATOR_CHAT_ID, keyboard=False)
            await send_message_to_chat("Оператор отключен. Вы снова общаетесь с ботом.", chat_id)

        elif 'reply_to_message' in data['message']:
            original_message = data['message']['reply_to_message']['text']
            if chat_status == "operator":
                await send_message_to_chat(
                    f"Сообщение от пользователя {chat_id}.\nОтвет на: {original_message}\n{text}",
                    OPERATOR_CHAT_ID,
                    keyboard=False
                )
            else:
                await process_openai_message(text, chat_id)

        else:
            if chat_status == "operator":
                await send_message_to_chat(f"Сообщение от пользователя {chat_id}.\n{text}", OPERATOR_CHAT_ID, keyboard=False)
            elif chat_status == "bot":
                await process_openai_message(text, chat_id)
    except Exception as e:
        logger.error(f"Exception: {str(e)}")

# TEST PURPOSE

@app.get("/redis_ping/")
async def redis_ping():
    logger.info("Pinging Redis")
    try:
        pong = await redis.ping()
        if pong:
            return {"message": "Redis is connected"}
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Redis connection failed")

@app.post("/redis_set_get/")
async def set_and_get_redis_key(key: str, value: str):
    logger.info(f"Setting and getting Redis key: {key}")
    try:
        await redis.set(key, value)
        stored_value = await redis.get(key)
        return {"message": "Key set and retrieved successfully", "key": key, "stored_value": stored_value}
    except Exception as e:
        logger.error(f"Failed to set and get key in Redis: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to set and get key in Redis")

@app.get('/redis_get/')
async def get_redis_key(key: str):
    logger.info(f"Getting Redis key: {key}")
    try:
        stored_value = await redis.get(key)
        return {"val": stored_value}
    except Exception as e:
        logger.error(f"Failed to get key in Redis: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get key in Redis")
