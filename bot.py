import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from deepface import DeepFace

# --- КОНФИГУРАЦИЯ ---
# Токен бота загружается из переменных окружения Railway (Environment Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN", "7851053002:AAHYlFzZ7bpT7gknQdSena2FUFbrf8UZ3wg")

# Директории для хранения верифицированных лиц и временных файлов
KNOWN_FACES_DIR = "known_faces"
TEMP_DIR = "temp"

# Автоматическое создание папок
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Настройка системы логирования
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- СОСТОЯНИЯ (FSM) ---
class SearchStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_name = State()
    waiting_for_photo = State()

# --- КЛАВИАТУРЫ ---
def get_main_menu() -> ReplyKeyboardMarkup:
    """Формирует главное меню взаимодействия с ботом."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поиск по номеру"), KeyboardButton(text="👤 Поиск по ФИО")],
            [KeyboardButton(text="🖼 Анализ / Сравнение фото"), KeyboardButton(text="ℹ️ О сервисе")]
        ],
        resize_keyboard=True
    )

def get_cancel_menu() -> ReplyKeyboardMarkup:
    """Формирует кнопку отмены текущего действия."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

# --- ОБРАБОТЧИКИ БАЗОВЫХ КОМАНД ---

@dp.message(CommandStart())
@dp.message(F.text == "❌ Отмена")
async def cmd_start(message: types.Message, state: FSMContext):
    """Обрабатывает команду /start и сбрасывает текущие состояния."""
    await state.clear()
    await message.answer(
        "👋 **Добро пожаловать в OSINT & Verification Bot!**\n\n"
        "Выберите интересующую функцию в меню ниже:\n"
        "• **Поиск по номеру** — анализ цифрового следа и оператора\n"
        "• **Поиск по ФИО** — проверка по открытым реестрам\n"
        "• **Анализ фото** — биометрическая верификация и обратный поиск",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "ℹ️ О сервисе")
async def cmd_about(message: types.Message):
    """Выводит справку о принципах работы бота."""
    await message.answer(
        "ℹ️ **Информация о сервисе:**\n\n"
        "Бот предназначен для агрегации информации из открытых публичных источников (Surface Web), "
        "генерации параметров поиска и локальной биометрической верификации.\n\n"
        "⚠️ *Все операции выполняются исключительно в рамках легального правового поля.*",
        parse_mode="Markdown"
    )

# --- МОДУЛЬ 1: ПОИСК ПО НОМЕРУ ТЕЛЕФОНА ---

@dp.message(F.text == "📱 Поиск по номеру")
async def start_phone_search(message: types.Message, state: FSMContext):
    """Запрашивает номер телефона у пользователя."""
    await state.set_state(SearchStates.waiting_for_phone)
    await message.answer(
        "📱 Введите номер телефона в формате `+79991112233`:",
        reply_markup=get_cancel_menu(),
        parse_mode="Markdown"
    )

@dp.message(SearchStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    """Генерирует поисковые ссылки по открытым реестрам для номера."""
    phone = message.text.strip()
    status_msg = await message.answer("🔄 *Сканирование публичных индексов...*", parse_mode="Markdown")
    
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    
    response = (
        f"📱 **Анализ номера:** `{phone}`\n\n"
        f"🔹 **Цифровой след (Google Dorks):**\n"
        f"• [Поиск VK](https://www.google.com/search?q=site:vk.com+\"{clean_phone}\")\n"
        f"• [Поиск Telegram](https://www.google.com/search?q=site:t.me+\"{clean_phone}\")\n"
        f"• [Поиск объявлений Avito](https://www.google.com/search?q=site:avito.ru+\"{clean_phone}\")\n\n"
        f"🏛 **Официальные реестры:**\n"
        f"• [Проверка DEF-кода (ЦНИИС)](https://www.rosreestr.ru)\n"
    )
    
    await status_msg.edit_text(response, parse_mode="Markdown", disable_web_page_preview=True)
    await state.clear()
    await message.answer("Выберите следующее действие:", reply_markup=get_main_menu())

# --- МОДУЛЬ 2: ПОИСК ПО ФИО ---

@dp.message(F.text == "👤 Поиск по ФИО")
async def start_name_search(message: types.Message, state: FSMContext):
    """Запрашивает ФИО у пользователя."""
    await state.set_state(SearchStates.waiting_for_name)
    await message.answer(
        "👤 Введите ФИО (например: *Иванов Иван Иванович*):",
        reply_markup=get_cancel_menu(),
        parse_mode="Markdown"
    )

@dp.message(SearchStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    """Формирует реестровые ссылки для поиска по имени."""
    query = message.text.strip()
    status_msg = await message.answer("🔄 *Формирование запросов к публичным реестрам...*", parse_mode="Markdown")
    
    response = (
        f"👤 **Запрос:** `{query}`\n\n"
        f"🌐 **Поисковые индексы:**\n"
        f"• [Поиск в Google](https://www.google.com/search?q=\"{query}\")\n"
        f"• [Поиск в Yandex](https://yandex.ru/search/?text=\"{query}\")\n\n"
        f"🏛 **Публичные государственные реестры:**\n"
        f"• [Банк данных исполнительных производств ФССП](https://fssp.gov.ru/)\n"
        f"• [Проверка статуса самозанятого (ФНС)](https://npd.nalog.ru/check-status/)\n"
        f"• [Реестр наследственных дел](https://notariat.ru/)"
    )
    
    await status_msg.edit_text(response, parse_mode="Markdown", disable_web_page_preview=True)
    await state.clear()
    await message.answer("Выберите следующее действие:", reply_markup=get_main_menu())

# --- МОДУЛЬ 3: АНАЛИЗ И СРАВНЕНИЕ ФОТО ---

@dp.message(F.text == "🖼 Анализ / Сравнение фото")
async def start_photo_search(message: types.Message, state: FSMContext):
    """Запрашивает загрузку фотографии."""
    await state.set_state(SearchStates.waiting_for_photo)
    await message.answer(
        "🖼 Отправьте фотографию человека для локального биометрического анализа и получения ссылок обратного поиска:",
        reply_markup=get_cancel_menu()
    )

@dp.message(SearchStates.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    """Скачивает фото, проводит сравнение лиц с помощью DeepFace и создает обратные поисковые ссылки."""
    status_msg = await message.answer("🔄 *Загрузка и обработка изображения...*", parse_mode="Markdown")
    
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = file.file_path
    
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    
    temp_local_path = os.path.join(TEMP_DIR, f"{message.from_user.id}_{photo.file_id}.jpg")
    await bot.download(photo, destination=temp_local_path)

    matched_person = None
    try:
        # Векторное сравнение с известными лицами в папке known_faces
        dfs = DeepFace.find(
            img_path=temp_local_path, 
            db_path=KNOWN_FACES_DIR, 
            model_name="VGG-Face",
            enforce_detection=False
        )
        if len(dfs) > 0 and not dfs[0].empty:
            matched_file_path = dfs[0].iloc[0]['identity']
            matched_person = os.path.basename(matched_file_path).split('.')[0]
    except Exception as e:
        logging.error(f"Ошибка биометрической обработки: {e}")

    # Удаление временного файла
    if os.path.exists(temp_local_path):
        os.remove(temp_local_path)

    # Клавиатура с кнопками обратного поиска по картинке
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Google Lens", url=f"https://lens.google.com/uploadbyurl?url={file_url}")],
        [InlineKeyboardButton(text="Yandex Images", url=f"https://yandex.ru/images/search?rpt=imageview&url={file_url}")]
    ])

    res_text = "🖼 **Результаты анализа изображения:**\n\n"
    if matched_person:
        res_text += f"✅ **Локальная база:** Найдено совпадение — `{matched_person}`\n\n"
    else:
        res_text += "❌ **Локальная база:** Совпадений среди верифицированных лиц не найдено.\n\n"

    res_text += "🌐 Для поиска первоисточника фото в глобальной сети используйте кнопки ниже:"

    await status_msg.delete()
    await message.answer(res_text, reply_markup=inline_kb, parse_mode="Markdown")
    await state.clear()
    await message.answer("Выберите следующее действие:", reply_markup=get_main_menu())

# --- ТОЧКА ВХОДА ---
async def main():
    """Запускает long polling для бота."""
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())