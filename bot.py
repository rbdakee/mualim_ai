import telebot
import os, difflib
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from PIL import Image, ImageDraw, ImageFont
from main_ai import check_quran_ayah
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
    "ayah_1":"بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ",
    "ayah_2":"الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
    "ayah_3":"الرَّحْمَنِ الرَّحِيمِ",
    "ayah_4":"مَالِكِ يَوْمِ الدِّينِ",
    "ayah_5":"إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ",
    "ayah_6":"اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ",
    "ayah_7":"صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ"
}

user_progress = {}

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Практиковать буквы"))
    markup.add(KeyboardButton("Практиковать Аль-Фатиху"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "✨ **Добро пожаловать в бот для изучения арабского языка!** ✨\n\n"
        "📚 Здесь вы можете:\n"
        "1️⃣ Практиковать **произношение арабских букв**\n"
        "2️⃣ Практиковать **чтение суры Аль-Фатиха**\n\n"
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

@bot.message_handler(func=lambda message: message.text == "Практиковать Аль-Фатиху")
def start_quran_practice(message):
    chat_id = message.chat.id
    user_progress[chat_id] = {"lesson": "quran_practice", "index": 0}
    bot.reply_to(message, "📖 Начинаем практику суры Аль-Фатиха!")
    send_next_ayah(chat_id)

def send_next_ayah(chat_id):
    lesson_data = user_progress.get(chat_id)
    if not lesson_data:
        return
    
    index = lesson_data["index"]
    if index >= len(quran_ayahs):
        bot.send_message(chat_id, "🎉 Практика Аль-Фатихи завершена! Отличная работа! ✅")
        del user_progress[chat_id]
        return
    
    ayah = list(quran_ayahs.values())[index]
    bot.send_message(chat_id, f"📖 Произнесите этот аят:\n**{ayah}**", parse_mode="Markdown")
    bot.send_message(chat_id, "🎙️ Отправьте голосовое сообщение с произношением.")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    chat_id = message.chat.id
    if chat_id not in user_progress:
        bot.reply_to(message, "⚠️ Ошибка: начните с выбора режима.")
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
        is_correct, transcription, mess = check_quran_ayah(file_path, correct_letter)
    elif lesson_type == "quran_practice":
        correct_ayah = list(quran_ayahs.values())[index]
        is_correct, transcription, mess = check_quran_ayah(file_path, correct_ayah)
        error_highlight, feedback = highlight_mistake(correct_ayah, transcription)
    
    if mess=='text':
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
    else:
        error_message = f"❌ Ошибка на сервере!\n Попробуйте снова:\n**{correct_ayah if lesson_type == 'quran_practice' else correct_letter}**"
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

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
