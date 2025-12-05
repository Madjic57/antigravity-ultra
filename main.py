# Antigravity Ultra - Main Entry Point
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from config import config


def main():
    """Start Antigravity Ultra server"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║     ⚡ ANTIGRAVITY ULTRA                                  ║
    ║     IA Autonome Ultra-Performante                         ║
    ║                                                           ║
    ╠═══════════════════════════════════════════════════════════╣
    ║                                                           ║
    ║  🚀 Démarrage du serveur...                              ║
    ║                                                           ║
    ║  📍 URL: http://127.0.0.1:8000                           ║
    ║  📖 API Docs: http://127.0.0.1:8000/docs                 ║
    ║                                                           ║
    ║  Fonctionnalités:                                        ║
    ║    • Multi-modèles (Groq, Ollama)                        ║
    ║    • Agent autonome avec outils                          ║
    ║    • Recherche web                                       ║
    ║    • Exécution de code                                   ║
    ║    • Mémoire persistante                                 ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Check for API key
    if not config.groq_api_key:
        print("⚠️  GROQ_API_KEY non configurée!")
        print("   Créez un fichier .env avec: GROQ_API_KEY=votre_clé")
        print("   Ou définissez la variable d'environnement")
        print("   Obtenir une clé gratuite: https://console.groq.com")
        print()
    
    # Start server
    uvicorn.run(
        "api:app",
        host=config.host,
        port=config.port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
