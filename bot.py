from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot import types, TeleBot
import json, os, difflib

from main_ai import check_quran_ayah
from dotenv import load_dotenv

load_dotenv()

# ✅ Telegram Bot Token
TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = TeleBot(TOKEN)

file_base_path = "files/"

arabic_alphabet_path = f"{file_base_path}arabic_alphabet.json"
quran_ayahs_path = f"{file_base_path}quran_ayahs.json"
surah_mapping_path = f"{file_base_path}surah_mapping.json"


with open(arabic_alphabet_path, "r", encoding="utf-8") as file:
    arabic_alphabet = json.load(file)
with open(quran_ayahs_path, "r", encoding="utf-8") as file:
    quran_ayahs = json.load(file)
with open(surah_mapping_path, "r", encoding="utf-8") as file:
    surah_mapping = json.load(file)

user_progress = {}

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Практиковать буквы"))
    markup.add(KeyboardButton("Практиковать Коран"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "✨ **Добро пожаловать в бот для изучения арабского языка!** ✨\n\n"
        "📚 Здесь вы можете:\n"
        "1️⃣ Практиковать **произношение арабских букв**\n"
        "2️⃣ Практиковать **чтение Корана**\n\n"
        "🚀 **Выберите режим и начнем!**",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda message: message.text == "Практиковать буквы")
def start_letter_practice(message):
    chat_id = message.chat.id
    user_progress[chat_id] = {"lesson": "letter_practice", "index": 0}
    bot.reply_to(message, "📖 Начинаем практику букв!")
    send_next_letter(chat_id)

def send_next_letter(chat_id):
    lesson_data = user_progress.get(chat_id)
    if not lesson_data:
        return
    
    index = lesson_data["index"]
    letters = list(arabic_alphabet.keys())
    
    if index >= len(letters):
        bot.send_message(chat_id, "🎉 Практика букв завершена! Отличная работа! ✅")
        del user_progress[chat_id]
        return
    
    letter = letters[index]
    bot.send_message(chat_id, f"🔤 Произнесите эту букву: **{letter}**", parse_mode="Markdown")
    bot.send_message(chat_id, "🎙️ Отправьте голосовое сообщение с произношением.")

@bot.message_handler(func=lambda message: message.text == "Практиковать Коран")
def choose_surah(message):
    chat_id = message.chat.id

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for surah_name in surah_mapping.keys():
        keyboard.add(types.KeyboardButton(surah_name))

    bot.send_message(chat_id, "📖 Выберите суру для практики:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in surah_mapping)
def start_quran_practice(message):
    chat_id = message.chat.id
    surah_name = message.text
    surah_number = surah_mapping[surah_name]

    user_progress[chat_id] = {
        "lesson": "quran_practice", 
        "surah": surah_number,
        "index": 1, 
        "known_words": set()}

    bot.reply_to(message, f"Начинаем практику суры {surah_name}!")
    send_next_ayah(chat_id)

def send_next_ayah(chat_id):
    lesson_data = user_progress.get(chat_id)
    if not lesson_data:
        return
    surah_number = lesson_data["surah"]
    index = lesson_data["index"]
    if index > len(quran_ayahs[str(surah_number)]):
        bot.send_message(chat_id, "🎉 Практика этой суры закончена! Отличная работа! ✅\nХочешь приступить к следующей суре?", reply_markup=main_menu())
        del user_progress[chat_id]
        return
    ayah = quran_ayahs.get(surah_number).get(str(index)) # Could be str or int. Need to check it
    known_words = lesson_data["known_words"]
    remaining_words = [word for word in ayah.split() if word not in known_words]
    
    if not remaining_words:
        lesson_data["index"] += 1
        send_next_ayah(chat_id)
        return
    
    bot.send_message(chat_id, f"📖 Произнесите этот аят:\n**{' '.join(remaining_words)}**", parse_mode="Markdown")
    bot.send_message(chat_id, "🎙️ Отправьте голосовое сообщение с произношением.")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    chat_id = message.chat.id
    if chat_id not in user_progress:
        bot.reply_to(message, "⚠️ Ошибка: начните с выбора режима.")
        return
    progress = user_progress.get(chat_id)

    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    file_path = f"{chat_id}.ogg"

    downloaded_file = bot.download_file(file_info.file_path)
    with open(file_path, "wb") as f:
        f.write(downloaded_file)

    if progress["lesson"] == "letter_practice":
        handle_letter_voice(progress, file_path, message, chat_id)
    elif progress["lesson"] == "quran_practice":
        handle_ayah_voice(progress, file_path, message, chat_id)

def handle_letter_voice(progress, file_path, message, chat_id):
    correct_letter = list(arabic_alphabet.keys())[progress['index']]
    is_correct, transcription, mess = check_quran_ayah(file_path, correct_letter)
    os.remove(file_path)
    if mess=='text':
        if is_correct:
            bot.reply_to(message, "✅ Верно! Двигаемся дальше...")
            progress["index"] += 1
            send_next_letter(chat_id)
        else:
            error_message = f"❌ Ошибка! Попробуйте снова:\n**{correct_letter}**\n📝 Вы сказали:\n**{transcription}**"
            bot.reply_to(message, error_message, parse_mode="Markdown")
    else:
        error_message = f"❌ Ошибка на сервере!\n Попробуйте снова:\n**{correct_letter}**"
        bot.reply_to(message, error_message, parse_mode="Markdown")

import difflib

def highlight_mistake(correct_text, user_text):
    correct_words = correct_text.split()
    user_words = user_text.split()

    matcher = difflib.SequenceMatcher(None, correct_words, user_words)

    correct_read = []
    mistakes = []
    feedback = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            correct_read.extend(user_words[j1:j2])  # Correctly read words
        elif tag == "replace" or tag == "delete":
            mistake_word = ' '.join(correct_words[i1:i2]) if i1 < len(correct_words) else "(не распознано)"
            mistakes.append(mistake_word)
            feedback.append(f"🔴 Ошибка: **{mistake_word}** – попробуйте выговорить точнее и не спеша.")  
        elif tag == "insert":
            extra_word = ' '.join(user_words[j1:j2]) if j1 < len(user_words) else "(не распознано)"
            mistakes.append(extra_word)
            feedback.append(f"⚠️ Лишнее слово: **{extra_word}** – возможно, это случайная ошибка.")
    if correct_read:
        correct_text_display = "✅ Правильно:\n" + ' '.join(correct_read)  
    else: correct_text_display = None
    mistakes_display = "❌ Ошибки:\n" + (' '.join(mistakes) if mistakes else "Нет ошибок!")

    return correct_text_display, mistakes_display, "\n".join(feedback) if feedback else "🎉 Отлично, без ошибок!"



def handle_ayah_voice(progress, file_path, message, chat_id):
    ayah = quran_ayahs[str(progress["surah"])][str(progress["index"])]
    known_words = progress["known_words"]
    is_correct, transcription, mess = check_quran_ayah(file_path, ayah)
    correct_highlight, error_highlight, feedback = highlight_mistake(ayah, transcription)
    os.remove(file_path)

    if mess == 'text':
        correct_words = set(ayah.split())
        spoken_words = set(transcription.split())
        new_known_words = spoken_words & correct_words
        known_words.update(new_known_words)
        
        if known_words == correct_words:
            bot.reply_to(message, "✅ Верно! Двигаемся дальше...")
            progress["index"] += 1
            progress["known_words"] = set()
            send_next_ayah(chat_id)
        else:
            remaining_words = [word for word in ayah.split() if word not in known_words]
            error_message = f"Вы прочитали:\n**{transcription}**"
            if correct_highlight:
                error_message += f"\n**{correct_highlight}**\n**{error_highlight}**\n💡 Разбор:\n{feedback}"
                bot.reply_to(message, error_message, parse_mode="Markdown")
                new_message = f"💡 Ничего страшного, ошибки — часть обучения!\n📖 Попробуйте еще раз прочитать **аят или то, что дается вам сложно**\n\nВесь Аят:\n**{ayah}**"
                new_message += f"\nСложные части:\n🔹 **{' '.join(remaining_words)}**"
                new_message += "\n\n📖 Попробуйте еще раз! Я уверен, у вас получится! 😊"
            else:
                error_message += f"\n\nВесь аят был прочитан неверно, но ничего страшного"
                bot.reply_to(message, error_message, parse_mode="Markdown")
                new_message = f"Видимо вы прочитали что-то другое или я не смог распознать то, что вы прочитали.\nПовторите еще раз аят:\n{ayah}"
                
            bot.send_message(chat_id, new_message, parse_mode="Markdown")
    else:
        bot.reply_to(message, transcription)


if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()