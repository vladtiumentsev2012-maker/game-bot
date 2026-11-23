import asyncio
import io
import os
import re
from threading import Thread
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from flask import Flask
from openai import AsyncOpenAI

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

client = AsyncOpenAI(
    api_key=MISTRAL_API_KEY,
    base_url="https://mistral.ai",
)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

user_limits = {}
MAX_FREE_GAMES = 2

GAME_PROMPT = """
Ты — гениальный разработчик HTML5 мини-игр. Создай полностью рабочую, увлекательную и красивую игру по описанию пользователя.
Правила:
1. Весь код (HTML, CSS, JS) строго в ОДНОМ файле. Без внешних картинок и звуков.
2. Графику рисуй на HTML5 Canvas (градиенты, частицы, анимация). Звуки генерируй через Web Audio API.
3. Обязательны: экран старта с кнопкой ИГРАТЬ, счетчик очков и экран проигрыша с кнопкой ЗАНОВО.
4. Управление должно работать и с клавиатуры (ПК), и тапами/свайпами по экрану (телефон).
5. Выведи ТОЛЬКО чистый HTML-код, начиная с <!DOCTYPE html>. Без лишних слов.
"""

app = Flask("")


@app.route("/")
def home():
  return "Бот работает!"


def run_web():
  app.run(host="0.0.0.0", port=8080)


@dp.message(CommandStart())
async def start_cmd(message: types.Message):
  await message.answer(
      "🎮 Привет! Я ИИ-создатель игр.\n\n"
      "Напиши идею любой мини-игры, и я пришлю готовый файл, который откроется"
      f" прямо в браузере.\nУ тебя есть **{MAX_FREE_GAMES} бесплатные"
      " генерации**!",
      parse_mode="Markdown",
  )


@dp.message()
async def create_game(message: types.Message):
  user_id = message.from_user.id
  used = user_limits.get(user_id, 0)

  if used >= MAX_FREE_GAMES:
    await message.answer(
        "⛔ Твои бесплатные попытки закончились! Напиши админу для"
        " продолжения."
    )
    return

  status_msg = await message.answer(
      "🕹 Создаю игру... Подожди 15–30 секунд."
  )

  try:
    response = await client.chat.completions.create(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": GAME_PROMPT},
            {"role": "user", "content": f"Создай игру: {message.text}"},
        ],
        temperature=0.7,
    )

    raw_text = response.choices[0].message.content
    match = re.search(
        r"(<!DOCTYPE html>.*</html>)", raw_text, re.DOTALL | re.IGNORECASE
    )
    html_code = match.group(1) if match else raw_text

    file_bytes = io.BytesIO(html_code.encode("utf-8"))
    game_file = types.BufferedInputFile(file_bytes.read(), filename="game.html")

    user_limits[user_id] = used + 1
    left = MAX_FREE_GAMES - user_limits[user_id]

    await message.answer_document(
        document=game_file,
        caption=(
            f"✅ **Игра готова!** Осталось попыток: {left}\n\nСкачай файл и"
            " открой в браузере (Chrome / Safari)."
        ),
        parse_mode="Markdown",
    )
  except Exception as e:
    await message.answer(f"⚠️ Ошибка нейросети, попробуй еще раз: {e}")
  finally:
    await status_msg.delete()


async def main():
  Thread(target=run_web).start()
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
