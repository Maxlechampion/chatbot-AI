import secrets
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, Blueprint
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth = Blueprint('auth', __name__)

# ============================================
# ROUTES EXISTANTES
# ============================================

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            user.reset_token = None
            user.reset_token_expiry = None
            db.session.commit()
            return redirect(url_for('chat.index'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Un compte existe déjà.', 'danger')
        else:
            hashed = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, email=email, password_hash=hashed)
            db.session.add(new_user)
            db.session.commit()
            flash('Inscription réussie ! Connectez-vous.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# ============================================
# ROUTES : REINITIALISATION DE MOT DE PASSE
# ============================================

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            print(f"\n{'='*60}")
            print(f"TOKEN DE REINITIALISATION pour {user.email}")
            print(f"URL : http://127.0.0.1:5000/reset-password/{token}")
            print(f"{'='*60}\n")
            
            flash('Un lien de réinitialisation a été généré. Vérifiez votre console.', 'info')
        else:
            flash('Si cet email existe, un lien a été envoyé.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html')


@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        flash('Ce lien est invalide ou a expiré.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
        elif len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
        else:
            user.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            user.reset_token = None
            user.reset_token_expiry = None
            db.session.commit()
            flash('Votre mot de passe a été réinitialisé ! Connectez-vous.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', token=token)