import replicate
import os
import logging
import time
import json
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import requests
from config import Config
from models import db, Conversation, Message
from urllib.parse import quote


# Configuration du logging
logging.basicConfig(level=logging.DEBUG)

chat = Blueprint('chat', __name__)

# ========== FONCTIONS DE RECHERCHE WEB ==========
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup

def search_web(query: str, max_results: int = 3) -> list:
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({"title": r.get('title'), "href": r.get('href'), "body": r.get('body')})
        return results
    except Exception as e:
        print(f"Erreur recherche: {e}")
        return []

def extract_page_content(url: str, max_chars: int = 2000) -> str:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator='\n', strip=True)
        text = ' '.join(text.split())
        return text[:max_chars] + "..." if len(text) > max_chars else text
    except Exception as e:
        print(f"Erreur extraction: {e}")
        return ""

@chat.route('/')
@login_required
def index():
    return render_template('index.html', models=Config.FREE_MODELS)

@chat.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.updated_at.desc()).all()
    sessions = [{"id": str(c.id), "name": c.name} for c in conversations]
    return jsonify(sessions)

@chat.route('/api/sessions', methods=['POST'])
@login_required
def create_session():
    data = request.get_json()
    name = data.get('name', None)
    default_model = Config.FREE_MODELS[0]["id"]
    new_conv = Conversation(name=name or "Nouvelle conversation", model_id=default_model, author=current_user)
    db.session.add(new_conv)
    db.session.commit()
    return jsonify({"session_id": str(new_conv.id)})

@chat.route('/api/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    conv = Conversation.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    db.session.delete(conv)
    db.session.commit()
    return jsonify({"success": True})

@chat.route('/api/sessions/<int:session_id>', methods=['PATCH'])
@login_required
def update_session(session_id):
    data = request.get_json()
    conv = Conversation.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    if 'name' in data:
        conv.name = data['name']
    if 'model' in data:
        conv.model_id = data['model']
    db.session.commit()
    return jsonify({"success": True})

@chat.route('/api/sessions/<int:session_id>/messages', methods=['GET'])
@login_required
def get_messages(session_id):
    conv = Conversation.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    messages = [{"role": m.role, "content": m.content} for m in conv.messages]
    return jsonify({"messages": messages, "model": conv.model_id})

@chat.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    data = request.get_json()
    user_message = data.get('message')
    session_id = data.get('session_id')
    model_id = data.get('model')
    enable_search = data.get('enable_search', False)
    enable_reasoning = data.get('enable_reasoning', False)

    conv = Conversation.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    if model_id and model_id != conv.model_id:
        conv.model_id = model_id
        db.session.commit()

    if len(conv.messages) == 0:
        conv.name = user_message[:40].strip()
        if len(conv.name) > 35:
            conv.name = conv.name[:35] + "..."
        db.session.commit()

    search_results_text = None
    if enable_search:
        raw_results = search_web(user_message)
        if raw_results:
            search_results_text = "📄 Résultats de recherche web :\n\n"
            for i, res in enumerate(raw_results, 1):
                search_results_text += f"**Source {i}** : {res['title']}\nURL : {res['href']}\nExtrait : {res['body']}\n\n"
            first_url = raw_results[0]['href']
            page_content = extract_page_content(first_url)
            if page_content:
                search_results_text += f"---\n**Contenu détaillé** :\n{page_content}\n"
        else:
            search_results_text = "⚠️ Aucun résultat trouvé."

    history = [{"role": m.role, "content": m.content} for m in conv.messages]
    if enable_search and search_results_text:
        augmented_message = f"Question : {user_message}\n\n{search_results_text}\n\nRéponds en utilisant ces informations si pertinentes."
    else:
        augmented_message = user_message

    messages_for_api = history + [{"role": "user", "content": augmented_message}]

    final_model = conv.model_id
    if enable_reasoning and "deepseek" not in final_model and final_model != "openrouter/free":
        final_model = "deepseek/deepseek-r1:free"
        conv.model_id = final_model
        db.session.commit()

    headers = {
        "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "HIGHFIVE UNIVERSITY AI"
    }
    payload = {
        "model": final_model,
        "messages": messages_for_api,
        "max_tokens": 1500,
        "temperature": 0.7
    }
    if enable_reasoning:
        payload["reasoning"] = {"enabled": True}

    try:
        response = requests.post(Config.OPENROUTER_URL, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        result = response.json()
        if enable_reasoning and "reasoning_details" in result:
            reasoning = result['reasoning_details'].get('reasoning', '')
            final_answer = result['choices'][0]['message']['content']
            ai_message = f"**🧠 Raisonnement :**\n{reasoning}\n\n**💡 Réponse :**\n{final_answer}"
        else:
            ai_message = result['choices'][0]['message']['content']
        if not ai_message or not isinstance(ai_message, str) or ai_message.strip() == "":
            raise ValueError("Réponse vide")
        new_user_msg = Message(role='user', content=user_message, conversation=conv)
        new_ai_msg = Message(role='assistant', content=ai_message, conversation=conv)
        db.session.add_all([new_user_msg, new_ai_msg])
        conv.updated_at = db.func.now()
        db.session.commit()
        return jsonify({"reply": ai_message, "conversation_name": conv.name})
    except Exception as e:
        logging.exception("Erreur API")
        return jsonify({"error": str(e)}), 500

# ========== GÉNÉRATION D'IMAGES (FONCTIONNELLE) ==========
@chat.route('/api/generate-image', methods=['POST'])
@login_required
def generate_image():
    data = request.get_json()
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({"error": "prompt requis"}), 400

    try:
        from urllib.parse import quote
        # L'URL Pollinations d'origine
        original_url = f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        # L'URL de votre proxy local
        proxied_url = f"/api/proxy-image?url={quote(original_url)}"
        return jsonify({"image_url": proxied_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@chat.route('/api/proxy-image', methods=['GET'])
@login_required
def proxy_image():
    # Récupérer l'URL de l'image depuis la requête
    image_url = request.args.get('url')
    if not image_url:
        return "URL manquante", 400

    try:
        # Télécharger l'image depuis Pollinations
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        # Renvoyer l'image avec le bon type MIME
        return response.content, 200, {'Content-Type': response.headers['Content-Type']}
    except Exception as e:
        return f"Erreur lors du téléchargement: {e}", 500


# ========== PROXY POUR VIDÉO (identique à celui des images) ==========
@chat.route('/api/proxy-video', methods=['GET'])
@login_required
def proxy_video():
    """Proxy pour éviter les CORS lors de l'affichage des vidéos générées"""
    video_url = request.args.get('url')
    if not video_url:
        return "URL manquante", 400
    try:
        response = requests.get(video_url, stream=True, timeout=60)
        response.raise_for_status()
        # Renvoyer la vidéo avec son type MIME d'origine
        return response.content, 200, {'Content-Type': response.headers.get('Content-Type', 'video/mp4')}
    except Exception as e:
        print(f"Erreur proxy vidéo: {e}")
        return f"Erreur lors du téléchargement: {e}", 500

# ========== GÉNÉRATION DE VIDÉO (asynchrone) ==========
@chat.route('/api/generate-video', methods=['POST'])
@login_required
def generate_video():
    data = request.get_json()
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({"error": "prompt requis"}), 400

    headers = {
        "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Liste des modèles vidéo gratuits (à essayer si le premier échoue)
    models_to_try = [
        "google/veo-3.1-lite:free",
        "bytedance/seedance-2.0:free",
        "luma/ray:free",
        "openrouter/free"
    ]

    for model in models_to_try:
        print(f"Tentative avec le modèle vidéo: {model}")
        # 1. Soumettre la tâche
        submit_payload = {
            "model": model,
            "prompt": prompt,
            "duration": 5,           # secondes (5 à 10 selon modèle)
            "aspect_ratio": "16:9"
        }
        try:
            submit_resp = requests.post("https://openrouter.ai/api/v1/videos", headers=headers, json=submit_payload, timeout=30)
            if submit_resp.status_code != 200:
                print(f"Échec soumission avec {model}: {submit_resp.status_code}")
                continue
            job_data = submit_resp.json()
            job_id = job_data.get('id')
            if not job_id:
                continue

            # 2. Polling (attente du résultat)
            for attempt in range(45):   # 45 tentatives max = environ 4 minutes
                time.sleep(5)
                poll_resp = requests.get(f"https://openrouter.ai/api/v1/videos/{job_id}", headers=headers)
                if poll_resp.status_code != 200:
                    continue
                poll_data = poll_resp.json()
                if poll_data['status'] == 'completed':
                    direct_url = poll_data['output']['video_url']
                    proxied_url = f"/api/proxy-video?url={quote(direct_url, safe='')}"
                    return jsonify({"video_url": proxied_url})
                elif poll_data['status'] == 'failed':
                    break  # ce modèle a échoué, passer au suivant
            print(f"Modèle {model} : délai d'attente ou échec")
        except Exception as e:
            print(f"Erreur avec {model}: {e}")
            continue

    # Si aucun modèle n'a fonctionné
    return jsonify({"error": "Aucun modèle vidéo gratuit n'est actuellement disponible. Veuillez réessayer plus tard."}), 500