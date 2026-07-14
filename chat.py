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
        logging.error(f"Erreur recherche DuckDuckGo: {e}")
        return []

def extract_page_content(url: str, max_chars: int = 2000) -> str:
    try:
        # Ajout d'un User-Agent pour éviter d'être banni/bloqué par les sites web
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

    # Sécurisation du typage de session_id (conversion de str vers int)
    try:
        session_id = int(session_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Identifiant de session invalide ou manquant"}), 400

    conv = Conversation.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    
    # Mise à jour du modèle si changé
    if model_id and model_id != conv.model_id:
        conv.model_id = model_id
        db.session.commit()
    
    # Mise à jour de la longueur si changée
    if length_mode != conv.response_length:
        conv.response_length = length_mode
        db.session.commit()

    if len(conv.messages) == 0:
        conv.name = user_message[:40].strip()
        if len(conv.name) > 35:
            conv.name = conv.name[:35] + "..."
        db.session.commit()

    # Récupérer les paramètres de longueur
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
    
    # System prompt basé sur la longueur choisie
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
    
    # Note : Le paramètre custom "reasoning" a été retiré ici pour éviter de déclencher des erreurs 400 Bad Request.
    # OpenRouter gère automatiquement le retour des tokens de raisonnement pour le modèle DeepSeek R1.

    try:
        response = requests.post(Config.OPENROUTER_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        choices = result.get('choices', [])
        if not choices:
            raise ValueError("Aucun choix (choices) renvoyé par l'API OpenRouter")

        message_data = choices[0].get('message', {})
        final_answer = message_data.get('content', '')

        # Extraction correcte du raisonnement selon le format OpenRouter (clé 'reasoning' ou 'reasoning_content')
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
        conv.updated_at = db.func.now()
        db.session.commit()
        return jsonify({"reply": ai_message, "conversation_name": conv.name})
    except Exception as e:
        logging.exception("Erreur lors de l'appel à l'API de discussion")
        return jsonify({"error": str(e)}), 500

# ========== GÉNÉRATION D'IMAGES ==========
@chat.route('/api/generate-image', methods=['POST'])
@login_required
def generate_image():
    data = request.get_json()
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({"error": "prompt requis"}), 400

    try:
        original_url = f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        proxied_url = f"/api/proxy-image?url={quote(original_url)}"
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

# ========== GÉNÉRATION DE VIDÉO (Utilise désormais Replicate) ==========
@chat.route('/api/generate-video', methods=['POST'])
@login_required
def generate_video():
    data = request.get_json()
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({"error": "prompt requis"}), 400

    # Vérification de la présence du token Replicate
    replicate_token = os.environ.get("REPLICATE_API_TOKEN") or getattr(Config, 'REPLICATE_API_TOKEN', None)
    if not replicate_token:
        return jsonify({"error": "Le jeton REPLICATE_API_TOKEN est manquant dans l'environnement."}), 500

    try:
        logging.info(f"Génération vidéo demandée avec Replicate pour le prompt : {prompt}")
        
        # Appel du modèle de génération vidéo via Replicate (ex: Zeroscope, très rapide et idéal pour le dev)
        # Assure-toi que REPLICATE_API_TOKEN est bien exporté dans ton environnement système.
        output = replicate.run(
            "anotherjesse/zeroscope-v2-xl:9f74767d61211111111111111111111111111111111111111111111111111111",
            input={
                "prompt": prompt,
                "num_frames": 24,
                "fps": 8,
                "width": 576,
                "height": 320
            }
        )

        # Replicate retourne généralement une liste d'URLs, nous prenons la première
        if isinstance(output, list) and len(output) > 0:
            direct_url = output[0]
        else:
            direct_url = output

        if not direct_url:
            raise ValueError("Aucune URL vidéo n'a pu être récupérée de Replicate.")

        proxied_url = f"/api/proxy-video?url={quote(direct_url, safe='')}"
        return jsonify({"video_url": proxied_url})

    except Exception as e:
        logging.exception("Échec de la génération de vidéo via Replicate")
        return jsonify({"error": f"La génération vidéo a échoué : {str(e)}"}), 500