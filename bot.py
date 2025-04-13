import os, json, difflib, sqlalchemy as sa
import threading
from sqlalchemy.orm import sessionmaker, declarative_base
from telebot import TeleBot, types
from datetime import datetime, timedelta
from main_ai import check_quran_ayah
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = TeleBot(TOKEN)

# Подключаем файл с аятами
quran_ayahs_path = "files/quran_ayahs.json"
with open(quran_ayahs_path, "r", encoding="utf-8") as file:
    quran_ayahs = json.load(file)

user_progress = {}
user_data = {}

# Получаем текст суры Аль-Фатиха
surah_fatiha = quran_ayahs.get("1", {})  # "1" - номер Аль-Фатихи в Коране
fatiha_ayahs = [surah_fatiha[str(i)] for i in range(1, len(surah_fatiha) + 1)]

# Настройка базы данных
DATABASE_URL = "sqlite:///users.db"
engine = sa.create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    chat_id = sa.Column(sa.Integer, primary_key=True)
    phone_number = sa.Column(sa.String, nullable=True)
    name = sa.Column(sa.String, nullable=False)
    age = sa.Column(sa.Integer, nullable=False)
    tajweed_studied = sa.Column(sa.String, nullable=False)
    teacher = sa.Column(sa.String, nullable=True)
    target = sa.Column(sa.String, nullable=False)
    al_fatiha_trials = sa.Column(sa.String)
    al_fatiha_done = sa.Column(sa.Boolean, nullable=False)
    last_session = sa.Column(sa.DateTime, nullable=False)
    want_trial = sa.Column(sa.Boolean, nullable=False)


Base.metadata.create_all(engine)

# Функция для создания inline-кнопок
def create_inline_keyboard(buttons):
    markup = types.InlineKeyboardMarkup()
    for text, callback in buttons:
        markup.add(types.InlineKeyboardButton(text, callback_data=callback))
    return markup

# Запрос имени
@bot.message_handler(commands=['menu'])
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = int(message.chat.id)
    existing_user = session.query(User).filter_by(chat_id=chat_id).first()
    if existing_user:
        chat_id = existing_user.chat_id
        user_data[chat_id] = {
            "name": existing_user.name,
            "age": existing_user.age,
            "tajweed_studied": existing_user.tajweed_studied,
            "teacher": existing_user.teacher,
            "target": existing_user.target,
            "phone_number": existing_user.phone_number,
            "al_fatiha_trials": existing_user.al_fatiha_trials,
            "al_fatiha_done": existing_user.al_fatiha_done,
            "last_session": existing_user.last_session,
            "want_trial": existing_user.want_trial
        }
        
        if user_data[chat_id].get("al_fatiha_done", False):
            buttons = [("Редактировать профиль", "edit_profile"), ("Практика Аль-Фатихи", "al_fatiha_practice"),
               ("Записаться на пробный урок", "trial_book")]
        else:
            buttons = [("Редактировать профиль", "edit_profile"), ("Практика Аль-Фатихи", "al_fatiha_practice")]
        bot.send_message(chat_id, f"📌 Добро пожаловать, {existing_user.name}!", reply_markup=create_inline_keyboard(buttons))
    else:
        chat_id = message.chat.id
        bot.send_message(chat_id, "📌 Добро пожаловать! Перед началом проверки Аль-Фатихи ответьте на несколько вопросов.")
        msg = bot.send_message(chat_id, "📛 Введите ваше имя:")
        user_data[chat_id] = {}
        user_data[chat_id]["delete"] = [msg.message_id]

@bot.callback_query_handler(func=lambda call: call.data == "edit_profile")
def edit_profile(call):
    chat_id = call.message.chat.id
    bot.delete_message(chat_id, call.message.message_id)
    user = session.query(User).filter_by(chat_id=chat_id).first()
    if not user:
        bot.answer_callback_query(call.id, "Ошибка: пользователь не найден.")
        return
    
    profile_text = (
        f"👤 *Ваш профиль:*\n"
        f"📛 Имя: {user.name}\n"
        f"📅 Возраст: {user.age}\n"
        f"📖 Уровень таджвида: {user.tajweed_studied}\n"
        f"👨‍🏫 Учился: {user.teacher}\n"
        f"🎯 Цель: {user.target}\n"
        f"📱 Телефон: {user.phone_number}\n"
    )
    bot.send_message(chat_id, profile_text, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data == "trial_book")
def trial_book(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    bot.delete_message(chat_id, call.message.message_id)
    send_trial_lesson_info(chat_id)


@bot.callback_query_handler(func=lambda call: call.data == "al_fatiha_practice")
def al_fatiha_practice(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    bot.delete_message(chat_id, call.message.message_id)
    bot.send_message(chat_id, "🧠 Запускаем практику Аль-Фатихи...")
    start_quran_practice(chat_id)


@bot.message_handler(func=lambda message: message.chat.id in user_data and "name" not in user_data[message.chat.id])
def get_name(message):
    chat_id = message.chat.id
    message_id = message.message_id
    user_data[chat_id]["name"] = message.text
    for msg_id in user_data[chat_id].get("delete", []):
        bot.delete_message(chat_id, msg_id)
    user_data[chat_id]["delete"].clear()
    bot.delete_message(chat_id, message_id)
    msg = bot.send_message(chat_id, "📅 Введите ваш возраст:")
    user_data[chat_id]["delete"].append(msg.message_id)

@bot.message_handler(func=lambda message: message.chat.id in user_data and "age" not in user_data[message.chat.id])
def get_age(message):
    chat_id = message.chat.id
    message_id = message.message_id
    bot.delete_message(chat_id, message_id)
    if not message.text.isdigit():
        msg = bot.send_message(chat_id, "⚠️ Введите корректный возраст (числом).")
        user_data[chat_id]["delete"].append(msg.message_id)
        return
    user_data[chat_id]["age"] = int(message.text)
    
    for msg_id in user_data[chat_id].get("delete", []):
        bot.delete_message(chat_id, msg_id)
    user_data[chat_id]["delete"].clear()

    buttons = [("Нет, с нуля", "tajweed_none"), ("Знаю алфавит", "tajweed_alphabet"),
               ("Умею читать", "tajweed_read"), ("Знаю правила таджвида", "tajweed_rules")]
    bot.send_message(chat_id, "📖 Изучали ли вы таджвид раньше?", reply_markup=create_inline_keyboard(buttons))

@bot.callback_query_handler(func=lambda call: call.data.startswith("tajweed_"))
def get_tajweed_studied(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    tajweed_mapping = {
        "tajweed_none": "Нет, с нуля",
        "tajweed_alphabet": "Знаю алфавит",
        "tajweed_read": "Умею читать",
        "tajweed_rules": "Знаю правила таджвида"
    }
    user_data[chat_id]["tajweed_studied"] = tajweed_mapping[call.data]

    if call.data in ["tajweed_read", "tajweed_rules"]:
        buttons = [("Самостоятельно", "teacher_self"), ("С устазом", "teacher_tutor")]
        bot.edit_message_text("📚 С кем вы изучали таджвид?",chat_id, message_id, reply_markup=create_inline_keyboard(buttons))
    else:
        ask_target(chat_id, message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("teacher_"))
def get_teacher(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    teacher_mapping = {
        "teacher_self": "Самостоятельно",
        "teacher_tutor": "С устазом"
    }
    user_data[chat_id]["teacher"] = teacher_mapping[call.data]
    ask_target(chat_id, message_id)

def ask_target(chat_id, message_id):
    buttons = [("Изучать религию углубленно", "target_religion"),
               ("Читать/учить Коран", "target_quran"),
               ("Изучать арабский", "target_arabic")]
    bot.edit_message_text("🎯 Какова ваша цель изучения?", chat_id, message_id, reply_markup=create_inline_keyboard(buttons))

@bot.callback_query_handler(func=lambda call: call.data.startswith("target_"))
def get_study_target(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    target_mapping = {
        "target_religion": "Изучать религию углубленно",
        "target_quran": "Читать/учить Коран",
        "target_arabic": "Изучать арабский"
    }
    user_data[chat_id]["target"] = target_mapping[call.data]

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton("📞 Отправить номер телефона", request_contact=True)
    keyboard.add(button)
    bot.delete_message(chat_id, message_id)
    bot.send_message(chat_id, "📱 Пожалуйста, отправьте ваш номер телефона.", reply_markup=keyboard)

@bot.message_handler(content_types=['contact'])
def get_phone_number(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone_number"] = message.contact.phone_number

    user_is_saved_message = save_user_to_db(chat_id)
    
    msg = user_is_saved_message.get("msg")

    bot.send_message(chat_id, msg, reply_markup=types.ReplyKeyboardRemove())
    start_quran_practice(chat_id)

def save_user_to_db(chat_id):
    existing_user = session.query(User).filter_by(chat_id=chat_id).first()
    if existing_user:
        return {"code": 401, "msg": f"Ошибка! Вы уже зарегестрированы, {existing_user.name}", "user": existing_user}
    data = user_data[chat_id]
    new_user = User(
        chat_id = chat_id,
        phone_number=data["phone_number"],
        name=data["name"],
        age=data["age"],
        tajweed_studied=data["tajweed_studied"],
        teacher=data.get("teacher", "Не изучал"),
        target=data["target"],
        al_fatiha_done = False,
        last_session = datetime.now(),
        want_trial = False
    )
    session.add(new_user)
    session.commit()
    del user_data[chat_id]
    return {"code":200, "msg": "✅ Спасибо! Теперь можно начинать проверку Аль-Фатихи!", "user": new_user}

def start_quran_practice(chat_id):

    user_progress[chat_id] = {
        "lesson": "quran_practice", 
        "surah": 1,
        "index": 1, 
        "known_words": set(),
        "attempts": 0,
        "start_time": datetime.now()}

    bot.send_message(chat_id, f"Начинаем проверку суры Аль Фатиха!")
    send_next_ayah(chat_id)

    threading.Timer(900, check_practice_timeout, args=[chat_id]).start()
    threading.Timer(1800, check_practice_timeout, args=[chat_id]).start()

def check_practice_timeout(chat_id):
    progress = user_progress.get(chat_id)
    if not progress or progress["lesson"] != "quran_practice":
        return
    progress['count'] = 0

    # Проверим, прошло ли 15 минут и практика ещё не завершена
    if (datetime.now() - progress["start_time"] >= timedelta(minutes=15) and progress['count'] == 0) or (datetime.now() - progress["start_time"] >= timedelta(minutes=30) and progress['count'] == 1):
        # Сохраняем текущие попытки
        update_ayah_attempt(chat_id, progress["attempts"])

        # Удаляем прогресс, чтобы не мешался
        del user_progress[chat_id]

        # Отправляем сообщение
        bot.send_message(chat_id, "⏳ Похоже, вы не завершили практику Аль-Фатихи. Но не переживайте!\n\n"
                                  "👨‍🏫 Вы можете записаться на *пробный урок*, где устаз лично поможет вам.\n"
                                  "Нажмите кнопку ниже, и наш менеджер свяжется с вами.")
        send_trial_lesson_info(chat_id)
        progress['count']+=1


def send_trial_lesson_info(chat_id):
    text = (
        "📌 *Группы набираются быстро, поэтому количество пробных уроков ограничено!* "
        "Сейчас урок можно пройти по акционной цене всего *990 тг* вместо *5000 тг*! 🎉\n\n"
        "📖 На пробном уроке устаз:\n"
        "✅ Оценит ваш текущий уровень таджвида\n"
        "✅ Объяснит, как вы сможете полностью доучить таджвид\n"
        "✅ Предоставит доступ к *бесплатным материалам* для самостоятельного изучения\n\n"
        "💡 Если вам интересно, нажмите кнопку ниже, и наш менеджер свяжется с вами!"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📅 Записаться на пробный урок", callback_data="trial_lesson"))
    markup.add(types.InlineKeyboardButton("Не интересно", callback_data="trial_not_interested"))

    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "trial_lesson")
def trial_lesson_handler(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)  # удаляем кнопки

    user = session.query(User).filter_by(chat_id=chat_id).first()
    
    if user:
        user.want_trial = True
        session.commit()

        text = (
            "⌛ Ожидайте звонка от нашего менеджера в ближайшее время.\n\n"
            "📚 Менеджер расскажет вам подробнее про урок и запишет вас на него.\n"
            "🤲 Пусть Аллах облегчит ваше стремление к знаниям!\n\n"
            "Вы всегда можете продолжать практиковать доступные для вас суры здесь - /menu"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "⚠️ Произошла ошибка: пользователь не найден.")


@bot.callback_query_handler(func=lambda call: call.data == "trial_not_interested")
def trial_not_interested(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None) 
    bot.send_message(chat_id, "👌 Хорошо, если появится интерес — вы всегда можете записаться позже во вкладке - /menu")


def send_next_ayah(chat_id):
    lesson_data = user_progress.get(chat_id)
    if not lesson_data:
        return
    surah_number = lesson_data["surah"]
    index = lesson_data["index"]
    if index > len(quran_ayahs[str(surah_number)]):
        bot.send_message(chat_id, "🎉 Отличная работа! Вы сдали суру Аль Фатиха ✅")
        user = session.query(User).filter_by(chat_id=chat_id).first()
        if user:
            user.al_fatiha_done = True
            session.commit()
        send_trial_lesson_info(chat_id)
        # update_to_db_lesson_data()
        del user_progress[chat_id]
        return
    audio_ayah = open(f"files/{surah_number}_{index}.mp3", 'rb')
    ayah = quran_ayahs.get(str(surah_number)).get(str(index))
    transcript = ayah[1]
    ayah = ayah[0]
    known_words = lesson_data["known_words"]
    remaining_words = [word for word in ayah.split() if word not in known_words]
    
    if not remaining_words:
        lesson_data["index"] += 1
        send_next_ayah(chat_id)
        return
    
    bot.send_audio(chat_id, audio_ayah, caption=f"📖 Произнесите этот аят:\n**{ayah}**\n_{transcript}_", title="Mishary Rashid Alafasy", parse_mode="Markdown")
    bot.send_message(chat_id, "🎙️ Отправьте голосовое сообщение с произношением.")
    audio_ayah.close()

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    
    chat_id = message.chat.id
    if chat_id not in user_progress:
        bot.reply_to(message, "⚠️ Ошибка: начните с выбора режима.")
        return
    progress = user_progress.get(chat_id)
    progress["attempts"] += 1

    if progress.get('mistake_msg', None) != None:
        bot.edit_message_reply_markup(chat_id, progress.get('mistake_msg'), reply_markup=None)
        user_progress[chat_id]['mistake_msg'] = None


    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    file_path = f"{chat_id}.ogg"

    downloaded_file = bot.download_file(file_info.file_path)
    with open(file_path, "wb") as f:
        f.write(downloaded_file)
    if progress["lesson"] == "quran_practice":
        handle_ayah_voice(progress, file_path, message, chat_id)

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
    ayah = quran_ayahs[str(progress["surah"])][str(progress["index"])][0]
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
            bot.reply_to(message, f"✅ Верно! Вы справились с {progress['attempts']} попытки(ок).")
            
            # ⬇️ вызываем нашу новую функцию:
            update_ayah_attempt(chat_id, progress["attempts"])
            
            # сбрасываем прогресс
            progress["index"] += 1
            progress["known_words"] = set()
            progress["attempts"] = 0
            send_next_ayah(chat_id)

        else:
            
            remaining_words = [word for word in ayah.split() if word not in known_words]
            error_message = f"Вы прочитали:\n**{transcription}**\n Попробуйте прочитать аят еще раз"
            buttons = [("Узнать свои ошибки", "check_errors"), ("Показать аят", "next_try")]
            markup = create_inline_keyboard(buttons)
            if correct_highlight:
                user_progress[chat_id]["last_feedback"] = error_message+f"\n\n**{correct_highlight}**\n**{error_highlight}**\n💡 Разбор:\n{feedback}"
                msg = bot.reply_to(message, error_message, parse_mode="Markdown", reply_markup = markup)
            else:
                user_progress[chat_id]["last_feedback"] = error_message+f"\n\nВесь аят был прочитан неверно, но ничего страшного"
                msg = bot.reply_to(message, error_message, parse_mode="Markdown", reply_markup = markup)
            user_progress[chat_id]['mistake_msg'] = msg.message_id
    else:
        bot.reply_to(message, transcription)

def update_ayah_attempt(chat_id: int, attempt_count: int):
    user = session.query(User).filter_by(chat_id=chat_id).first()
    if user:
        # Берём текущую строку попыток, если нет — создаём
        current_trials = user.al_fatiha_trials or ""
        new_trials = current_trials + ("," if current_trials else "") + str(attempt_count)
        user.al_fatiha_trials = new_trials
        session.commit()
        print(f"[+] Обновлены попытки для chat_id={chat_id}: {user.al_fatiha_trials}")
    else:
        print(f"[!] Пользователь с chat_id={chat_id} не найден в базе.")


@bot.callback_query_handler(func=lambda call: call.data in ["check_errors", "next_try"])
def next_try(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    if call.data == 'check_errors':
        new_text = user_progress[chat_id].get("last_feedback", "Ошибка!")
        buttons = [(("Показать аят", "next_try"))]
        bot.edit_message_text(new_text, chat_id, message_id, reply_markup=create_inline_keyboard(buttons), parse_mode="Markdown")
    elif call.data == 'next_try':
        user_progress[chat_id]['last_feedback'] = ''
        user_progress[chat_id]['mistake_msg'] = None
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
        send_next_ayah(chat_id)

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()  
