import requests, os, time
from dotenv import load_dotenv

load_dotenv()

HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN')
# LETTER_MODEL = "HamzaSidhu786/arabic-alphabet-speech-classification"
QURAN_MODEL = "tarteel-ai/whisper-base-ar-quran"

HEADERS = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}

def transcribe_audio(file_path, model):
    tries = 0
    with open(file_path, "rb") as f:
        data = f.read()
        response = requests.post(f"https://api-inference.huggingface.co/models/{model}", headers=HEADERS, data=data)
        while response.status_code != 200 and tries<=3:
            time.sleep(0.6)
            tries+=1
            response = requests.post(f"https://api-inference.huggingface.co/models/{model}", headers=HEADERS, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f'❌ Ошибка на сервере - {response.status_code}, {response.reason}.\nПовторите еще раз'}
    

# def check_pronunciation(file_path, correct_letter):
#     transcription = transcribe_audio(file_path, QURAN_MODEL)
#     if 'text' in transcription:
#         transcription = transcription.get('text')
#     else:
#         transcription = transcription.get('error')
#         # transcription = transcription[0].get('label')
#     return correct_letter in transcription, transcription

def check_quran_ayah(file_path, correct_ayah):
    transcription = transcribe_audio(file_path, QURAN_MODEL)
    if 'text' in transcription:
        mess = 'text'
    else:
        mess = 'error'
    transcription = transcription.get(mess)
    return correct_ayah in transcription, transcription, mess
