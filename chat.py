import replicate
import os
import logging
import time
import json
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from config import Config
from models import db, Conversation, Message
from urllib.parse import quote
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)

chat = Blueprint('chat', __name__)

# ========== CONSTANTES POUR AGNES AI ==========
AGNES_API_BASE = "https://apihub.agnes-ai.com"
AGNES_VIDEO_URL = f"{AGNES_API_BASE}/v1/videos"
AGNES_STATUS_URL = f"{AGNES_API_BASE}/agnesapi"  # Pour interroger le statut

# ========== FONCTIONS DE RECHERCHE WEB ==========
def search_web(query: str, max_results: int = 3) -> list:
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({"title": r.get('title'), "href": r.get('href'), "body": r.get('body')})
        return results
    except Exception as e:
        logging.error(f"Erreur recherche DuckDuckGo: {e}")
        return []

def extract_page_content(url: str, max_chars: int = 2000) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator='\n', strip=True)
        text = ' '.join(text.split())
        return text[:max_chars] + "..." if len(text) > max_chars else text
    except Exception as e:
        logging.error(f"Erreur extraction de la page {url}: {e}")
        return ""

# ========== ROUTES ==========
@chat.route('/')
@login_required
def index():
    return render_template('index.html', models=Config.FREE_MODELS, lengths=Config.RESPONSE_LENGTHS)

@chat.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.updated_at.desc()).all()
    sessions = [{"id": str(c.id), "name": c.name, "length": c.response_length} for c in conversations]
    return jsonify(sessions)

@chat.route('/api/sessions', methods=['POST'])
@login_required
def create_session():
    data = request.get_json()
    name = data.get('name', None)
    length = data.get('length', Config.DEFAULT_LENGTH)
    default_model = Config.FREE_MODELS[0]["id"]
    new_conv = Conversation(
        name=name or "Nouvelle conversation", 
        model_id=default_model, 
        response_length=length,
        author=current_user
    )
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
    if 'length' in data:
        conv.response_length = data['length']
    db.session.commit()
    return jsonify({"success": True})

@chat.route('/api/sessions/<int:session_id>/messages', methods=['GET'])
@login_required
def get_messages(session_id):
    conv = Conversation.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    messages = [{"role": m.role, "content": m.content} for m in conv.messages]
    return jsonify({"messages": messages, "model": conv.model_id, "length": conv.response_length})

@chat.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    data = request.get_json()
    user_message = data.get('message')
    session_id = data.get('session_id')
    model_id = data.get('model')
    length_mode = data.get('length', 'medium')
    enable_search = data.get('enable_search', False)
    enable_reasoning = data.get('enable_reasoning', False)

    try:
        session_id = int(session_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Identifiant de session invalide ou manquant"}), 400

    conv = Conversation.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    
    if model_id and model_id != conv.model_id:
        conv.model_id = model_id
        db.session.commit()
    
    if length_mode != conv.response_length:
        conv.response_length = length_mode
        db.session.commit()

    if len(conv.messages) == 0:
        conv.name = user_message[:40].strip()
        if len(conv.name) > 35:
            conv.name = conv.name[:35] + "..."
        db.session.commit()

    length_config = Config.RESPONSE_LENGTHS.get(length_mode, Config.RESPONSE_LENGTHS[Config.DEFAULT_LENGTH])

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
                search_results_text += f"---\n**Contenu détaillé de la source principale** :\n{page_content}\n"
        else:
            search_results_text = "⚠️ Aucun résultat trouvé sur le web."

    history = [{"role": m.role, "content": m.content} for m in conv.messages]
    
    system_prompt = length_config["system_prompt"]
    
    if enable_search and search_results_text:
        augmented_message = f"Question de l'utilisateur : {user_message}\n\n{search_results_text}\n\nRéponds en utilisant ces informations si elles sont pertinentes. Sois précis."
    else:
        augmented_message = user_message

    messages_for_api = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": augmented_message}]

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
        "max_tokens": length_config["max_tokens"],
        "temperature": length_config["temperature"],
        "top_p": Config.TOP_P,
        "frequency_penalty": Config.FREQUENCY_PENALTY,
        "presence_penalty": Config.PRESENCE_PENALTY,
    }

    try:
        response = requests.post(Config.OPENROUTER_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        choices = result.get('choices', [])
        if not choices:
            raise ValueError("Aucun choix (choices) renvoyé par l'API OpenRouter")

        message_data = choices[0].get('message', {})
        final_answer = message_data.get('content', '')

        reasoning = message_data.get('reasoning') or message_data.get('reasoning_content') or ""

        if enable_reasoning and reasoning:
            ai_message = f"**🧠 Raisonnement :**\n{reasoning}\n\n**💡 Réponse :**\n{final_answer}"
        else:
            ai_message = final_answer
            
        if not ai_message or not isinstance(ai_message, str) or ai_message.strip() == "":
            raise ValueError("La réponse générée est vide.")
            
        new_user_msg = Message(role='user', content=user_message, conversation=conv)
        new_ai_msg = Message(role='assistant', content=ai_message, conversation=conv)
        db.session.add_all([new_user_msg, new_ai_msg])
        conv.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"reply": ai_message, "conversation_name": conv.name})
    except Exception as e:
        logging.exception("Erreur lors de l'appel à l'API de discussion")
        return jsonify({"error": str(e)}), 500

# ========== GÉNÉRATION D'IMAGES (Pollinations.ai) ==========
@chat.route('/api/generate-image', methods=['POST'])
@login_required
def generate_image():
    data = request.get_json()
    prompt = data.get('prompt')
    session_id = data.get('session_id')
    if not prompt:
        return jsonify({"error": "prompt requis"}), 400
    if not session_id:
        return jsonify({"error": "session_id requis"}), 400

    conv = Conversation.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()

    try:
        original_url = f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        proxied_url = f"/api/proxy-image?url={quote(original_url)}"
        
        # Sauvegarde des messages dans l'historique
        user_msg = Message(role='user', content=f"/image {prompt}", conversation=conv)
        ai_msg = Message(role='assistant', content=f"![Image générée]({proxied_url})", conversation=conv)
        db.session.add_all([user_msg, ai_msg])
        conv.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({"image_url": proxied_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat.route('/api/proxy-image', methods=['GET'])
@login_required
def proxy_image():
    image_url = request.args.get('url')
    if not image_url:
        return "URL manquante", 400

    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        return response.content, 200, {'Content-Type': response.headers['Content-Type']}
    except Exception as e:
        return f"Erreur lors du téléchargement: {e}", 500

# ========== PROXY POUR VIDÉO ==========
@chat.route('/api/proxy-video', methods=['GET'])
@login_required
def proxy_video():
    video_url = request.args.get('url')
    if not video_url:
        return "URL manquante", 400
    try:
        response = requests.get(video_url, stream=True, timeout=60)
        response.raise_for_status()
        return response.content, 200, {'Content-Type': response.headers.get('Content-Type', 'video/mp4')}
    except Exception as e:
        logging.error(f"Erreur proxy vidéo: {e}")
        return f"Erreur lors du téléchargement: {e}", 500
@chat.route('/api/generate-video', methods=['POST'])
@login_required
def generate_video():
    data = request.get_json()
    prompt = data.get('prompt')
    session_id = data.get('session_id')
    if not prompt:
        return jsonify({"error": "prompt requis"}), 400
    if not session_id:
        return jsonify({"error": "session_id requis"}), 400

    conv = Conversation.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()

    api_key = Config.AGNES_API_KEY
    if not api_key:
        logging.error("❌ Clé API Agnes manquante")
        return jsonify({"error": "Clé API Agnes manquante. Veuillez configurer AGNES_API_KEY dans .env"}), 500

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 1. Création de la tâche
    payload = {
        "model": "agnes-video-v2.0",
        "prompt": prompt,
        "height": 480,
        "width": 640,
        "num_frames": 25,
        "frame_rate": 8
    }

    try:
        logging.info(f"🎬 Création d'une tâche vidéo Agnes pour : {prompt}")
        # Timeout augmenté à 60 secondes pour la création
        response = requests.post(AGNES_VIDEO_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        task_data = response.json()
        logging.info(f"📦 Réponse brute de création : {task_data}")

        video_id = task_data.get('video_id') or task_data.get('task_id')
        if not video_id:
            logging.error(f"❌ Aucun ID trouvé dans la réponse : {task_data}")
            return jsonify({"error": "Impossible de récupérer l'ID de la tâche."}), 500

        logging.info(f"✅ Tâche créée avec succès. ID : {video_id}")

        # 2. Polling pour récupérer le résultat
        max_attempts = 60  # 60 * 5s = 300s max (5 minutes)
        attempt = 0
        video_url = None

        while attempt < max_attempts:
            time.sleep(5)
            attempt += 1
            logging.info(f"🔄 Tentative de récupération {attempt}/{max_attempts}")

            status_url = f"{AGNES_STATUS_URL}?video_id={video_id}"
            try:
                status_response = requests.get(status_url, headers=headers, timeout=30)
                if status_response.status_code == 200:
                    result_data = status_response.json()
                    status = result_data.get('status')
                    logging.info(f"📊 Statut : {status}")
                    
                    if status == 'succeeded':
                        video_url = result_data.get('video_url') or result_data.get('output')
                        if video_url:
                            logging.info(f"🎬 Vidéo récupérée : {video_url}")
                            break
                    elif status in ['failed', 'error']:
                        error_msg = result_data.get('error', 'Erreur inconnue')
                        logging.error(f"❌ Échec de la génération : {error_msg}")
                        return jsonify({"error": f"Échec de la génération : {error_msg}"}), 500
                else:
                    logging.warning(f"⚠️ Statut HTTP inattendu : {status_response.status_code}")
            except requests.exceptions.Timeout:
                logging.warning("⏰ Timeout lors du polling, on réessaie...")
            except Exception as e:
                logging.warning(f"⚠️ Erreur lors du polling : {e}")

        if not video_url:
            logging.error("❌ Aucune vidéo récupérée après le polling")
            return jsonify({"error": "La génération vidéo a pris trop de temps ou a échoué."}), 500

        # 3. Sauvegarde des messages
        user_msg = Message(role='user', content=f"/video {prompt}", conversation=conv)
        ai_msg = Message(role='assistant', content=f"🎥 [Vidéo générée avec Agnes AI]({video_url})", conversation=conv)
        db.session.add_all([user_msg, ai_msg])
        conv.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"video_url": video_url})

    except requests.exceptions.Timeout:
        logging.exception("⏰ Timeout lors de la création de la tâche")
        return jsonify({"error": "Le service Agnes AI met trop de temps à répondre. Veuillez réessayer."}), 504
    except requests.exceptions.RequestException as e:
        logging.exception("❌ Erreur réseau lors de l'appel à Agnes AI")
        return jsonify({"error": f"Erreur de communication avec Agnes AI : {str(e)}"}), 500
    except Exception as e:
        logging.exception("❌ Erreur inattendue lors de la génération vidéo")
        return jsonify({"error": f"Erreur interne : {str(e)}"}), 500
