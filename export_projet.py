#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import fnmatch
import datetime

# ===== CONFIGURATION =====
# Dossier racine du projet (par défaut, le dossier où se trouve le script)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Nom du fichier de sortie
OUTPUT_FILE = "project_snapshot.txt"

# Dossiers et fichiers à ignorer (supports les motifs avec * et ?)
IGNORE_PATTERNS = [
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    "env",
    ".env",
    "dist",
    "build",
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.tmp",
    "*.swp",
    "*.swo",
    ".DS_Store",
    "project_snapshot.txt",  # ne pas inclure la sortie elle-même
]

# Extensions de fichiers binaires (à ignorer)
BINARY_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib",
    ".ico", ".webp"
}

# ===== FONCTIONS =====

def should_ignore(path):
    """Vérifie si le chemin ou le nom doit être ignoré."""
    basename = os.path.basename(path)
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(basename, pattern):
            return True
        # Vérifier aussi si le chemin complet contient un motif (ex: dossier/node_modules)
        if pattern in path.split(os.sep):
            return True
    return False

def is_binary(filepath):
    """Détecte si un fichier est binaire (par extension ou par contenu)."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in BINARY_EXTENSIONS:
        return True
    # Lecture des premiers octets pour détecter des caractères non imprimables
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:  # présence d'un octet nul => probablement binaire
                return True
        return False
    except Exception:
        return True  # si on ne peut pas lire, on ignore

def write_tree(out_file, root_dir, prefix=""):
    """Écrit l'arborescence des dossiers (simple) dans le fichier."""
    entries = sorted(os.listdir(root_dir))
    # Filtrer les entrées ignorées
    entries = [e for e in entries if not should_ignore(os.path.join(root_dir, e))]
    for i, entry in enumerate(entries):
        path = os.path.join(root_dir, entry)
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        out_file.write(prefix + connector + entry + "\n")
        if os.path.isdir(path):
            extension = "    " if is_last else "│   "
            write_tree(out_file, path, prefix + extension)

def write_file_content(out_file, filepath, relative_path):
    """Écrit le contenu d'un fichier texte."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Tentative avec un autre encodage
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception:
            out_file.write(f"\n⚠️  Impossible de lire le fichier (encodage non reconnu) : {relative_path}\n")
            return
    except Exception as e:
        out_file.write(f"\n⚠️  Erreur lors de la lecture de {relative_path} : {e}\n")
        return

    out_file.write(f"\n\n{'='*80}\n")
    out_file.write(f"FICHIER : {relative_path}\n")
    out_file.write('='*80 + "\n\n")
    out_file.write(content)
    # Ajouter un saut de ligne final si absent
    if content and not content.endswith('\n'):
        out_file.write('\n')

def main():
    print(f"📁 Export du projet depuis : {ROOT_DIR}")
    print(f"📄 Fichier de sortie : {OUTPUT_FILE}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        # En-tête
        out.write(f"=== SNAPSHOT DU PROJET ===\n")
        out.write(f"Date : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out.write(f"Racine : {ROOT_DIR}\n\n")

        # Arborescence
        out.write("=== ARBORESCENCE DU PROJET ===\n")
        out.write(ROOT_DIR + "\n")
        write_tree(out, ROOT_DIR)
        out.write("\n\n")

        # Parcourir tous les fichiers
        out.write("=== CONTENU DES FICHIERS ===\n")
        count = 0
        for root, dirs, files in os.walk(ROOT_DIR):
            # Ignorer les dossiers selon les motifs (on modifie dirs en place)
            dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d))]

            for file in files:
                filepath = os.path.join(root, file)
                if should_ignore(filepath):
                    continue
                relative = os.path.relpath(filepath, ROOT_DIR)
                if is_binary(filepath):
                    out.write(f"\n⚠️  Fichier binaire ignoré : {relative}\n")
                    continue
                write_file_content(out, filepath, relative)
                count += 1
                print(f"✔  Ajouté : {relative}")

        out.write("\n\n=== FIN DU SNAPSHOT ===\n")
        out.write(f"Nombre de fichiers inclus : {count}\n")

    print(f"\n✅ Export terminé. {count} fichiers inclus dans '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    main()