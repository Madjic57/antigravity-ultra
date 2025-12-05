# Antigravity Ultra

IA autonome ultra-performante avec agent, recherche web, et exécution de code.

## 🚀 Fonctionnalités

- **Multi-modèles** : Groq (gratuit & rapide) + Ollama (local)
- **Agent autonome** : Recherche web, fichiers, code Python
- **Mémoire persistante** : SQLite
- **Interface moderne** : Thème sombre, streaming temps réel

## ⚙️ Configuration

Créez un fichier `.env` :

```env
GROQ_API_KEY=gsk_votre_clé_ici
```

Obtenez une clé gratuite : https://console.groq.com

## 🏃 Lancement local

```bash
pip install -r requirements.txt
python main.py
```

Ouvrez http://localhost:8000

## ☁️ Déploiement Cloud

### Render.com (gratuit)

1. Fork ce repo sur GitHub
2. Connectez Render.com à votre GitHub
3. Créez un "New Web Service"
4. Ajoutez `GROQ_API_KEY` dans Environment Variables
5. Déployez !

## 📁 Structure

```
├── api.py           # FastAPI server
├── config.py        # Configuration
├── models.py        # LLM orchestration
├── agent/           # Agent engine + tools
├── memory/          # Persistence
└── static/          # Frontend
```

## 📜 License

MIT
