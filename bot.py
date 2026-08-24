import os
import sys
import logging
import asyncio

# Отключаем GUI-режим для OpenCV и Qt, чтобы избежать ошибок с libxcb на серверах Linux
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Получение токена Telegram из переменных окружения Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logging.error("КРИТИЧЕСКАЯ ОШИБКА: Переменная BOT_TOKEN не задана в Railway Variables!")

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()

# Главная клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📸 Проанализировать фото")],
        [KeyboardButton(text="ℹ️ О боте")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 Привет! Я бот для распознавания и анализа лиц.\n\n"
        "Отправь мне фотографию с лицом, и я определю возраст, пол и эмоции!",
        reply_markup=main_keyboard
    )

@dp.message(F.text == "ℹ️ О боте")
async def about_handler(message: Message):
    """Информация о боте"""
    await message.answer(
        "🤖 Бот работает на базе нейросетей **DeepFace** и **TensorFlow**.\n"
        "Он умеет распознавать ключевые параметры лица по фотографии.",
        parse_mode="Markdown"
    )

@dp.message(F.photo)
async def photo_handler(message: Message):
    """Обработка входящих фотографий"""
    await message.answer("⏳ Фотография получена, запускаю нейросеть...")
    
    file_path = f"temp_{message.photo[-1].file_id}.jpg"
    
    try:
        # Безопасный импорт DeepFace внутри функции
        from deepface import DeepFace
        
        # Загрузка фото из Telegram
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        await bot.download_file(file_info.file_path, file_path)
        
        # Выполнение тяжелого анализа в отдельном потоке
        loop = asyncio.get_running_loop()
        analysis = await loop.run_in_executor(
            None,
            lambda: DeepFace.analyze(
                img_path=file_path,
                actions=['age', 'gender', 'emotion'],
                enforce_detection=False
            )
        )
        
        # Разбор ответа нейросети
        res = analysis[0] if isinstance(analysis, list) else analysis
        age = res.get('age', 'Не определено')
        gender_dict = res.get('gender', {})
        gender = res.get('dominant_gender', 'Не определено')
        emotion = res.get('dominant_emotion', 'Не определено')
        
        # Перевод эмоций на русский
        emotions_ru = {
            'angry': 'Злость 😡',
            'disgust': 'Отвращение 🤢',
            'fear': 'Страх 😨',
            'happy': 'Радость 😊',
            'sad': 'Грусть 😢',
            'surprise': 'Удивление 😲',
            'neutral': 'Нейтральное 😐'
        }
        
        emotion_translated = emotions_ru.get(emotion.lower(), emotion)
        gender_translated = "Мужчина 👨" if gender.lower() == "man" else "Женщина 👩" if gender.lower() == "woman" else gender

        response_text = (
            f"📊 **Результаты анализа лица:**\n\n"
            f"👤 **Возраст:** ~{age} лет\n"
            f"⚧ **Пол:** {gender_translated}\n"
            f"🎭 **Преобладающая эмоция:** {emotion_translated}"
        )
        
        await message.answer(response_text, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Ошибка при анализе фотографии: {e}")
        await message.answer("⚠️ Не удалось распознать лицо на фотографии. Попробуйте прислать более чёткий снимок.")
        
    finally:
        # Очистка временного файла
        if os.path.exists(file_path):
            os.remove(file_path)

async def main():
    if not bot:
        logging.error("Запуск остановлен: не указан BOT_TOKEN.")
        return
    logging.info("Бот успешно запущен и принимает сообщения!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())