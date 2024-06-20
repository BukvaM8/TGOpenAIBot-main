import openai

from config import OPEN_AI_KEY, CHATGPT_MODEL


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