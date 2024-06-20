import requests

# Замените на ваш токен Telegram бота
TOKEN = '7204156061:AAGm_oS-eMFNO6N9gop2OGUnDe14RaXgvsM'
# Замените на ваш ID чата
CHAT_ID = '944413137'
MESSAGE = 'Тестовое сообщение'

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": MESSAGE
}

response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
