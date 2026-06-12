import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    FREE_MODELS = [
        {"id": "openrouter/free", "name": "🚀 Routeur automatique"},
        {"id": "google/gemini-2.0-flash-exp:free", "name": "Gemini 2.0 Flash"},
        {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B"},
        {"id": "deepseek/deepseek-r1:free", "name": "DeepSeek R1 (Raisonnement)"},
    ]
    IMAGE_MODELS = [
        {"id": "google/gemini-2.5-flash-image-preview:free", "name": "Gemini 2.5 Flash Image"},
        {"id": "flux/flux-2-pro:free", "name": "Flux 2 Pro"},
    ]
    VIDEO_MODELS = [
        {"id": "bytedance/seedance-2.0", "name": "Seedance 2.0"},
        {"id": "google/veo-3.1", "name": "Veo 3.1"},
        {"id": "wan/wan-2.7", "name": "Wan 2.7"},
    ]