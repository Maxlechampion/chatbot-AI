from werkzeug.security import generate_password_hash
from models import db, User
from app import create_app

app = create_app()

with app.app_context():
    # Liste tous les utilisateurs
    users = User.query.all()
    print("=" * 50)
    print("UTILISATEURS ENREGISTRES")
    print("=" * 50)
    for u in users:
        print(f"ID: {u.id} | Username: {u.username} | Email: {u.email}")
    print("=" * 50)

    # Changer le mot de passe d'un utilisateur
    username = input("\nNom d'utilisateur à modifier : ").strip()
    new_password = input("Nouveau mot de passe : ").strip()

    user = User.query.filter_by(username=username).first()
    if user:
        user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()
        print(f"\n✅ Mot de passe de '{username}' mis à jour avec succès !")
    else:
        print(f"\n❌ Utilisateur '{username}' introuvable.")