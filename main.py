import os
import httpx
import openai
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Инициализация FastAPI
app = FastAPI()

# Получаем переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Настраиваем OpenAI
openai.api_key = OPENAI_API_KEY

# Telegram API URL
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


class TelegramUpdate(BaseModel):
    update_id: int
    message: dict = None


async def send_telegram_message(chat_id: int, text: str) -> dict:
    """
    Отправляет сообщение пользователю через Telegram API.
    
    Args:
        chat_id: ID чата пользователя
        text: Текст сообщения для отправки
    
    Returns:
        dict: Ответ от Telegram API
    """
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def get_openai_response(text: str) -> str:
    """
    Получает ответ от OpenAI ChatGPT.
    
    Args:
        text: Текст пользователя для обработки
    
    Returns:
        str: Ответ от ChatGPT
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": text}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ошибка при обращении к OpenAI: {str(e)}"


@app.post("/webhook")
async def webhook(request: Request):
    """
    Эндпоинт для приема входящих обновлений от Telegram.
    """
    try:
        data = await request.json()
        
        # Проверяем, что это сообщение
        if "message" not in data:
            return JSONResponse({"ok": True})
        
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        
        # Обработка команды /start
        if text == "/start":
            welcome_message = (
                "Привет! Я бот, работающий с ChatGPT.\n"
                "Отправь мне любое сообщение, и я отвечу с помощью OpenAI."
            )
            await send_telegram_message(chat_id, welcome_message)
            return JSONResponse({"ok": True})
        
        # Если сообщение пустое (например, фото, стикер и т.д.)
        if not text:
            await send_telegram_message(
                chat_id, 
                "Пожалуйста, отправьте текстовое сообщение."
            )
            return JSONResponse({"ok": True})
        
        # Получаем ответ от OpenAI
        ai_response = await get_openai_response(text)
        
        # Отправляем ответ пользователю
        await send_telegram_message(chat_id, ai_response)
        
        return JSONResponse({"ok": True})
    
    except Exception as e:
        print(f"Ошибка при обработке webhook: {str(e)}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/")
async def root():
    """
    Корневой эндпоинт для проверки работы сервера.
    """
    return {"message": "Telegram GPT Bot is running"}


@app.post("/set-webhook")
async def set_webhook(webhook_url: str):
    """
    Настраивает webhook для Telegram бота.
    
    Args:
        webhook_url: URL для webhook (например, https://yourdomain.com/webhook)
    """
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN не установлен")
    
    url = f"{TELEGRAM_API_URL}/setWebhook"
    payload = {"url": webhook_url}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


@app.get("/webhook-info")
async def get_webhook_info():
    """
    Получает информацию о текущем webhook.
    """
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN не установлен")
    
    url = f"{TELEGRAM_API_URL}/getWebhookInfo"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


