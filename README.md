# Чатбот в Телеграме с возможностью отправлять запросы в OpenAI, связываться с оператором. 
Проект представляет собой интеграционный модуль, обеспечивающий взаимодействие между мессенджером Telegram и чат-ботом OpenAI API. Основной задачей проекта является обработка и передача сообщений, поступающих из Telegram, к чат-боту OpenAI, а также обратная отправка ответов пользователям. Пристувует логика связи с оператором для помощи пользователю.

Проект написан на Python 3.10.12 и активно использует возможности асинхронного программирования для обеспечения высокой производительности и эффективного управления ресурсами. В его основе лежат такие технологии, как:

asyncpg: для асинхронного взаимодействия с базой данных PostgreSQL.
sqlalchemy[asyncio]: для асинхронного ORM-управления базой данных.
aioredis: для работы с Redis в асинхронном режиме.
fastapi: для создания асинхронного веб-приложения, обеспечивающего прием и обработку вебхуков из Telegram и отправку запросов к OpenAI API.

Проект построен таким образом, чтобы минимизировать задержки и оптимально использовать сетевые и вычислительные ресурсы при взаимодействии между различными компонентами системы.
## Содержание

1. [Настройка проекта](#project-setup)
2. [Создание тунеля ngrok](#running-the-project)
3. [Структура проекта](#watch-the-structure)
4. [Описание фич](#features)
5. [requirements.txt](#requirements)
5. [Примеры использования](#testing)

## Настройка проекта
1. Склонируйте репозиторий:
   ```sh
    git clone https://github.com/BukvaM8/TGOpenAIBot-main.git
    cd dir
    ```
2. Создайте venv:
   ```sh
    python -m venv venv
    source venv/bin/activate  # на винде: venv\Scripts\activate
    ```
3. Установите requirements
   ```sh
    pip install -r requirements.txt
    ```
4. Добавьте свои ключи в .env (Особенно важен ключ OPERATOR_CHAT_ID, так пользователь сможет обратиться к оператору в случае проблемы. В файле .env Замените на полученное значение выполнения команды curl -s "https://api.telegram.org/bot<YOUR_TG_BOT_TOKEN>/getUpdates" в терминале).
5. Токен Telegram_api (В проекте он называется TG_BOT_TOKEN) вы получите после создания собственного бота в телеграме, через  BotFather.
6. Токен ChatGPt OpenAi API (В проекте называется  OPENAI_TOKEN )можно получить на их официальном сайте
7. Далее нужно разобраться с Ngrok 

   
## Создание тунеля ngrok
1. В директории с проектом запускаем следующую команду
     ```sh
      ngrok http http://localhost:8000
     ```
2. Полученный URL вставляем в .env
   ```sh
    NGROK_URL=your-ngrok-url
   ```
3. Ребилдим проект
    ```sh
    docker-compose up -d --build
    ```
4. Чтобы убедиться что вебхук работает в браузере отправляем запрос вида
   ```sh
   https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo
   ```
После всех этих действий пытаемся запустить проект через докер в терминале 

5. Билд проекта
   ```sh
   docker-compose up -d --build
   ```


## Структура проекта
папка source_code:

* **main.py**: Основной файл приложения с маршрутами FastAPI и обработкой вебхуков.
* **models.py**: Модели SQLAlchemy для таблиц базы данных.
* **db.py**: Настройка подключения к базе данных.
* **redis_client.py**: Настройка клиента Redis.
* **chatgpt.py**: Интеграция с ChatGPT.

корневая папка:
* **test_chatgpt.py: код предназначен для тестирования взаимодействия с ChatGPT, используя OpenAI API. 
* **test_telegram_api.py: код предназначен для отправки тестового сообщения в Telegram чат, используя Telegram API.

## Описание фич

1. Класс, взаимодействующий с openAI API (отправка сообщений в чат и получение ответа)

    ```python
   class ChatGPT:
    def __init__(self, api_key=OPEN_AI_KEY, model=CHATGPT_MODEL):
        self.api_key = api_key
        self.model = model
        self.conversation = []
        openai.api_key = self.api_key

    async def send_message(self, message, role='user', clear_conversation=False):
        if clear_conversation:
            await self.clear_conversation()
        self.conversation.append({'role': role, 'content': message})
        return message

    async def get_response(self):
        response = openai.ChatCompletion.create(model=self.model, messages=self.conversation)
        reply = response.choices[0].message['content']
        self.conversation.append({'role': 'assistant', 'content': reply})
        return reply

    async def clear_conversation(self):
        del self.conversation[1:]
   ```
2. Вебхук, реагирующий на сообщения, отправленные боту. 
   На вход принимаем json, далее забираем chat_id и text, они нам понадобятся для отправки сообщений пользователю и сохранения порядка ответа (в редисе сохраняем ключ-значение chat_id: "bot" | "operator").
   ```python 
   @app.post("/webhook/")
async def webhook(req: Request, db: AsyncSession = Depends(get_db)):
    logger.info("Received webhook event")
    try:
        data = await req.json()
        logger.info(f"Webhook data: {data}")
        chat_id = data['message']['chat']['id']
        text = data['message']['text'].strip().lower()
           .......
   ```
3. Обработка сценария взаимодействия с клиентом (диалог с ботом, диалог с оператором и первые слова бота)
  ```python 
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
   ```
4. Обработка сообщений оператора.
   В данной реализации бот является промежуточным звеном между клиентом и оператором. Сообщения, отправленные клиентом оператору бот перенаправляет на уже известный и определенный OPERATOR_CHAT_ID. Ответ оператора точно так же сквозь бота отправляется клиенту.
   Оператору приходит уведомления в виде 
   ```python
   f"Сообщение от пользователя {chat_id}\nОтветьте в формате chat_id: ответ\nmessage history"
   ```
   После ответа оператора вебхук ловит сообщение.
   ```python
   if chat_id == OPERATOR_CHAT_ID:
      await handle_operator_message(text)
      return
   ```
   
   В заданном формате мы парсим айди чата с клиентом и через апи бота отвечаем на вопрос.
   
   ```python
      async def handle_operator_message(message):
       try:
           client_id, reply = message.split(':', 1)
           await send_message_to_chat(f"Ответ оператора: {reply.strip()}", client_id.strip())
       except ValueError:
           await send_message_to_chat("Неверный формат сообщения. Используйте формат 'chat_id: сообщение'.",
                                      OPERATOR_CHAT_ID)
   ```
5. Интерфейс вызова оператора. Для удобства пользователя я сделал кнопку, при нажатии которой начнется чат с оператором. Повторное нажатие приведет к окончанию диалога с оператором и наш бот снова может принимать вопросы, на которые ответит с помощью openai.
   Кнопка не показывается у оператора. 
   ```python
   async def send_message_to_chat(text: str, chat_id: int):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if chat_id != OPERATOR_CHAT_ID:
        payload["reply_markup"] = {
            "keyboard": [[{"text": "Подключить/отключить оператора"}]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
   ```
6. Тычки для работы с redis, сделаны для удобства тестирования (поменять значение у чата bot/operator)
   ```python
   @app.post("/redis_set_get/")
   async def set_and_get_redis_key(key: str, value: str):
       try:
           await redis.set(key, value)
           stored_value = await redis.get(key)
           return {"message": "Key set and retrieved successfully", "key": key, "stored_value": stored_value}
       except Exception as e:
           raise HTTPException(status_code=500, detail="Failed to set and get key in Redis")


   @app.get('/redis_get/')
   async def get_redis_key(key: str):
       stored_value = await redis.get(key)
       return {"val": stored_value}
   ```
## requirements.txt
   ```sh
fastapi==0.70.0
uvicorn==0.15.0
aioredis==2.0.0
pyngrok==5.1.0
httpx==0.27
openai==0.28.1
databases
asyncpg 
sqlalchemy[asyncio]
python-dotenv
aiogram==2.23.1
pydantic==1.10.16

   ```

## Примеры использования 
1. Работа с редисом
   Простые ручки для изменений-созданий-получений redis записей
   ```sh
   curl "http://localhost:8000/redis_get/?key=test_key"
   curl -X POST "http://localhost:8000/redis_set_get/" -d '{"key": "test_key", "value": "test_value"}' -H "Content-Type: application/json"
   ```
2. Сценарий работы пользователя в ТГ боте
   Пользователь пишет боту (начинается диалог с команды /start), бот отвечает на это сообщением
   ```sh
   "Привет! Я ваш новый бот. Задайте мне любой вопрос и я отвечу. Нажмите кнопку для связи с оператором. Ваш номер чата {chat_id}"
   ```
   Далее бот открыт для любых вопросов (насколько чатгпт готов ответить)
   В любой моменте если есть какие-то проблемы,например, проблемы с OpenAi, пользователь может связаться с оператором, для этого реализована кнопка "Подключить оператора".
   Так же стоит уточнить что если есть проблемы с OpenAi то бот отправит сообщение в виде:
   "Проблема соединения с ChatGPT. Код ошибки: здесь будет описана ошибка"
   "Свяжитесь с оператором"

   
   
   После нажатия кнопки "Подключить оператора" пользователь получает сообщение "Подключаю оператора..." и "Оператор подключен. Можете отправлять сообщения."
   Оператор получает сообщение в виде: 
   "Сообщение от пользователя {chat_id}.
   "Текст сообщения"

   Так же если пользователь решит переслать сообщение оператору, то он может нажать "ответить" в выбранном сообщении, оно отобразится в внизу в поле ввода сообщения, пользователь может написать еще какой-то    текст, и после нажатия кнопки отправить, это сообщение , вместе с другим, отправится оператору.
   Оператор получит его в виде:
   "Сообщение от пользователя {chat_id}.
   Ответ на: Проблема соединения с ChatGPT. Код ошибки: RateLimitError - You exceeded your current quota, please check your plan and billing details. For more information on this error, read the docs:      https://platform.openai.com/docs/guides/error-codes/api-errors..
  Свяжитесь с оператором.
   "текст сообщения пользователя"

 Каждый ответ оператора обозначен строкой "Ответ оператора:" чтобы пользователь понимал, что говорит с живым человеком.
   Для взаимодействя оператора и бота необходимо соблюдать формат ответа chat_id: ответ, где chat_id это айди чата с пользователем (он придет в сообщении).
   После того как разговор завершен клиент сова нажимает кнопку , только в этот раз кнопка уже имеет вид "Отсоединить оператора"
   и получает сообщение "Отсоединяю оператора..." и "Оператор отключен. Вы снова общаетесь с ботом." . 
После этого ответа оператор перестает получать сообщения пользователя и пользователь снова может пользоваться ботом по назначению, кнопка для связи с оператором снова будет иметь вид "Подсоединить оператора", и наоборот "Отсоединить оператора" пока пользователь ее не нажмет.
# TGOpenAIBot-main
