import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    # Modèles optimisés pour les réponses longues
    FREE_MODELS = [
        {"id": "openrouter/free", "name": "🚀 Routeur automatique"},
        {"id": "google/gemini-2.0-flash-exp:free", "name": "Gemini 2.0 Flash"},
        {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B"},
        {"id": "deepseek/deepseek-r1:free", "name": "DeepSeek R1 (Raisonnement)"},
        {"id": "deepseek/deepseek-chat:free", "name": "DeepSeek V3 (Ultra-Long)"},
        {"id": "qwen/qwen-2.5-72b-instruct:free", "name": "Qwen 2.5 72B (Long)"},
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

    # Paramètres de longueur des réponses
    RESPONSE_LENGTHS = {
        "short": {
            "label": "⚡ Courte",
            "max_tokens": 500,
            "temperature": 0.3,
            "system_prompt": "Tu es un assistant IA concis et direct. Réponds de manière brève et précise. Utilise des phrases courtes. Maximum 100 mots.",
            "icon": "fa-bolt"
        },
        "medium": {
            "label": "📋 Moyenne", 
            "max_tokens": 1500,
            "temperature": 0.5,
            "system_prompt": "Tu es un assistant IA équilibré. Fournis des réponses complètes mais concises. Structure avec des paragraphes clairs. Environ 200-300 mots.",
            "icon": "fa-list"
        },
        "long": {
            "label": "📚 Longue",
            "max_tokens": 4000,
            "temperature": 0.7,
            "system_prompt": "Tu es un assistant IA expert et pédagogique. Fournis des réponses détaillées et structurées. Utilise des sections, exemples concrets, et analogies. Minimum 400 mots. Explique le 'pourquoi' et le 'comment'.",
            "icon": "fa-book"
        },
        "very_long": {
            "label": "🔥 Très longue",
            "max_tokens": 8000,
            "temperature": 0.8,
            "system_prompt": "Tu es un assistant IA expert universitaire. Fournis des réponses ultra-détaillées, exhaustives et approfondies. Structure avec introduction, développement approfondi, exemples multiples, cas pratiques, comparaisons, et conclusion récapitulative. Minimum 800 mots. Explore tous les aspects du sujet.",
            "icon": "fa-fire"
        }
    }
    
    # Paramètres par défaut
    DEFAULT_LENGTH = "medium"
    TOP_P = 0.95
    FREQUENCY_PENALTY = 0.1
    PRESENCE_PENALTY = 0.1