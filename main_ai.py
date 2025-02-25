import requests, os
from dotenv import load_dotenv

load_dotenv()

HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN')
# LETTER_MODEL = "HamzaSidhu786/arabic-alphabet-speech-classification"
QURAN_MODEL = "tarteel-ai/whisper-base-ar-quran"

HEADERS = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}

def transcribe_audio(file_path, model):
    with open(file_path, "rb") as f:
        data = f.read()
        response = requests.post(f"https://api-inference.huggingface.co/models/{model}", headers=HEADERS, data=data)
        
        print(response.status_code)
        if response.status_code == 200:
            return response.json()
        else:
            return {'text': 'Произошла ошибка, повторите еще раз'}
    

def check_pronunciation(file_path, correct_letter):
    transcription = transcribe_audio(file_path, QURAN_MODEL)
    print(transcription)
    # if 'text' in transcription:
    transcription = transcription.get('text')
    # else:
    #     transcription = transcription[0].get('label')
    return correct_letter in transcription, transcription

def check_quran_ayah(file_path, correct_ayah):
    transcription = transcribe_audio(file_path, QURAN_MODEL).get('text')
    return correct_ayah in transcription, transcription
