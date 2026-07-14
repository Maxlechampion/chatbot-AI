import sqlite3
import os

db_path = 'app.db'
if not os.path.exists(db_path):
    db_path = 'instance/app.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Vérifier si la colonne existe déjà
cursor.execute("PRAGMA table_info(conversation)")
columns = [col[1] for col in cursor.fetchall()]

if 'response_length' not in columns:
    cursor.execute("ALTER TABLE conversation ADD COLUMN response_length VARCHAR(20) DEFAULT 'medium'")
    print("Colonne 'response_length' ajoutée avec succès !")
else:
    print("Colonne 'response_length' déjà présente.")

conn.commit()
conn.close()
print("Migration terminée.")