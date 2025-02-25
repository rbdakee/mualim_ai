import telebot
import os, difflib
from main_ai import check_pronunciation, check_quran_ayah
from dotenv import load_dotenv

load_dotenv()

# ✅ Telegram Bot Token
TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = telebot.TeleBot(TOKEN)

# ✅ Arabic Alphabet Pronunciations
arabic_alphabet = {
    "ا": "ألف", "ب": "باء", "ت": "تاء", "ث": "ثاء",
    "ج": "جيم", "ح": "حاء", "خ": "خاء", "د": "دال",
    "ذ": "ذال", "ر": "راء", "ز": "زاي", "س": "سين",
    "ش": "شين", "ص": "صاد", "ض": "ضاد", "ط": "طاء",
    "ظ": "ظاء", "ع": "عين", "غ": "غين", "ف": "فاء",
    "ق": "قاف", "ك": "كاف", "ل": "لام", "م": "ميم",
    "ن": "نون", "ه": "هاء", "و": "واو", "ي": "ياء"
}
quran_ayahs = {
    "ayah_1": "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ",
    "ayah_2": "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
    "ayah_3": "الرَّحْمَنِ الرَّحِيمِ",
    "ayah_4": "مَالِكِ يَوْمِ الدِّينِ",
}

user_progress = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, 
        "✨ **Добро пожаловать в бот для изучения арабского языка!** ✨\n\n"
        "📚 Здесь вы можете:\n"
        "1️⃣ Практиковать **произношение арабских букв** – используйте команду `/letter_practice`\n"
        "2️⃣ Практиковать **чтение аятов Корана** – используйте команду `/quran_practice`\n\n"
        "🚀 **Выберите режим и начнем!**", 
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['letter_practice'])
def start_letter_practice(message):
    chat_id = message.chat.id
    user_progress[chat_id] = {"lesson": "letter_practice", "index": 0}
    bot.reply_to(message, "📖 Начинаем практику букв!\n", parse_mode="Markdown")
    send_next_letter(chat_id)

def send_next_letter(chat_id):
    lesson_data = user_progress.get(chat_id)

    if not lesson_data:
        bot.send_message(chat_id, "⚠️ Ошибка: начните с `/letter_practice`.")
        return

    index = lesson_data["index"]
    letters = list(arabic_alphabet.keys())

    if index >= len(letters):
        bot.send_message(chat_id, "🎉 Практика букв завершена! Отличная работа! ✅")
        del user_progress[chat_id]
        return

    letter = letters[index]
    bot.send_message(chat_id, f"🔤 Произнесите эту букву: **{letter}**", parse_mode="Markdown")

    audio_path = f"audio/{letter}.ogg"
    if os.path.exists(audio_path):
        with open(audio_path, "rb") as audio:
            bot.send_voice(chat_id, audio)
    
    bot.send_message(chat_id, "🎙️ Отправьте голосовое сообщение с произношением.")
@bot.message_handler(commands=['quran_practice'])
def start_quran_practice(message):
    chat_id = message.chat.id
    user_progress[chat_id] = {"lesson": "quran_practice", "index": 0}
    bot.reply_to(message, "📖 Начинаем практику аятов Корана!\n", parse_mode="Markdown")
    send_next_ayah(chat_id)

def send_next_ayah(chat_id):
    lesson_data = user_progress.get(chat_id)

    if not lesson_data:
        bot.send_message(chat_id, "⚠️ Ошибка: начните с `/quran_practice`.")
        return

    index = lesson_data["index"]
    ayahs = list(quran_ayahs.values())

    if index >= len(ayahs):
        bot.send_message(chat_id, "🎉 Практика аятов завершена! Отличная работа! ✅")
        del user_progress[chat_id]
        return

    ayah = ayahs[index]
    bot.send_message(chat_id, f"📖 Произнесите этот аят:\n**{ayah}**", parse_mode="Markdown")
    bot.send_message(chat_id, "🎙️ Отправьте голосовое сообщение с произношением.")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    chat_id = message.chat.id
    if chat_id not in user_progress:
        bot.reply_to(message, "⚠️ Ошибка: начните с `/letter_practice` или `/quran_practice`.")
        return

    lesson_type = user_progress[chat_id]["lesson"]
    index = user_progress[chat_id]["index"]

    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    file_path = f"{chat_id}.ogg"

    downloaded_file = bot.download_file(file_info.file_path)
    with open(file_path, "wb") as f:
        f.write(downloaded_file)

    if lesson_type == "letter_practice":
        correct_letter = list(arabic_alphabet.keys())[index]
        is_correct, transcription = check_pronunciation(file_path, correct_letter)
    elif lesson_type == "quran_practice":
        correct_ayah = list(quran_ayahs.values())[index]
        is_correct, transcription = check_quran_ayah(file_path, correct_ayah)
        error_highlight, feedback = highlight_mistake(correct_ayah, transcription)
    
    if is_correct:
        bot.reply_to(message, "✅ Верно! Двигаемся дальше...")
        user_progress[chat_id]["index"] += 1
        if lesson_type == "letter_practice":
            send_next_letter(chat_id)
        else:
            send_next_ayah(chat_id)
    else:
        error_message = f"❌ Ошибка! Попробуйте снова:\n**{correct_ayah if lesson_type == 'quran_practice' else correct_letter}**\n📝 Вы сказали:\n**{transcription}**"
        if lesson_type == "quran_practice":
            error_message += f"\n🔍 Ошибка в слове: **{error_highlight}**\n💡 Советы: {feedback}"
        bot.reply_to(message, error_message, parse_mode="Markdown")
    
    os.remove(file_path)

def highlight_mistake(correct_text, user_text):
    correct_words = correct_text.split()
    user_words = user_text.split()
    
    matcher = difflib.SequenceMatcher(None, correct_words, user_words)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal':
            error_word = ' '.join(user_words[j1:j2]) if j1 < len(user_words) else "(не распознано)"
            feedback = "Попробуйте лучше артикулировать букву или избежать добавления лишних букв." if error_word else "Постарайтесь говорить медленнее и четче."
            return error_word, feedback
    return "(не распознано)", "Попробуйте говорить четче."


# @bot.message_handler(content_types=["voice"])
# def handle_voice(message):
#     chat_id = message.chat.id
#     if chat_id not in user_progress:
#         bot.reply_to(message, "⚠️ Ошибка: начните с `/letter_practice` или `/quran_practice`.")
#         return

#     lesson_type = user_progress[chat_id]["lesson"]
#     index = user_progress[chat_id]["index"]

#     file_id = message.voice.file_id
#     file_info = bot.get_file(file_id)
#     file_path = f"{chat_id}.ogg"

#     downloaded_file = bot.download_file(file_info.file_path)
#     with open(file_path, "wb") as f:
#         f.write(downloaded_file)

#     if lesson_type == "letter_practice":
#         correct_letter = list(arabic_alphabet.keys())[index]
#         is_correct, transcription = check_pronunciation(file_path, correct_letter)

#     elif lesson_type == "quran_practice":
#         correct_ayah = list(quran_ayahs.values())[index]
#         is_correct, transcription = check_quran_ayah(file_path, correct_ayah)

#     if is_correct:
#         bot.reply_to(message, "✅ Верно! Двигаемся дальше...")
#         user_progress[chat_id]["index"] += 1
#         if lesson_type == "letter_practice":
#             send_next_letter(chat_id)
#         else:
#             send_next_ayah(chat_id)
#     else:
#         bot.reply_to(message, f"❌ Ошибка! Попробуйте снова:\n**{correct_letter if lesson_type == 'letter_practice' else correct_ayah}**\n📝 Вы сказали: **`{transcription}`**", parse_mode="Markdown")
#     os.remove(file_path)

# ✅ Run the bot
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
