# 🎯 HTTP Load Tester EDU - Version 4.0.0

## 📚 Version Éducative pour BTS SIO SISR

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-GPLv2-green.svg)
![Version](https://img.shields.io/badge/Version-4.0.0-brightgreen.svg)
![Education](https://img.shields.io/badge/Purpose-Educational-yellow.svg)

---

## ⚠️ AVERTISSEMENT IMPORTANT

**CET OUTIL EST STRICTEMENT RÉSERVÉ À UN USAGE ÉDUCATIF ET AUTORISÉ**

- ✅ **Autorisé** : Tests sur vos propres systèmes, environnements d'apprentissage, CTF
- ✅ **Autorisé** : Pentesting avec autorisation écrite explicite
- ✅ **Autorisé** : Projets académiques dans un cadre contrôlé (BTS SIO SISR, etc.)
- ❌ **INTERDIT** : Attaques contre des systèmes tiers sans autorisation
- ❌ **INTERDIT** : Utilisation contre des infrastructures critiques
- ❌ **INTERDIT** : Toute activité illégale ou non éthique

**L'utilisation non autorisée de cet outil est illégale et peut entraîner des poursuites pénales.**

---

## 📖 Table des Matières

1. [Introduction](#-introduction)
2. [Nouvelles Fonctionnalités](#-nouvelles-fonctionnalités-v400)
3. [Architecture](#-architecture)
4. [Installation](#-installation)
5. [Utilisation](#-utilisation)
6. [Dashboard Web](#-dashboard-web)
7. [Exemples](#-exemples)
8. [Objectifs Pédagogiques](#-objectifs-pédagogiques)
9. [Défenses Anti-DDoS](#-comprendre-les-défenses-anti-ddos)
10. [Dépannage](#-dépannage)

---

## 🎓 Introduction

Cette version professionnelle et pédagogique de l'outil de load testing a été complètement réécrite pour offrir :

- Une architecture moderne orientée objet
- Une performance optimale avec asyncio
- Un dashboard web interactif
- Un logging professionnel
- Des safeguards éducatifs intégrés

### Contexte BTS SIO SISR

Cet outil a été conçu pour les étudiants en BTS SIO SISR pour :
- Comprendre les attaques DDoS Layer 7
- Apprendre les bonnes pratiques de développement Python
- Étudier les mécanismes de défense
- Pratiquer le pentesting éthique

---

## 🚀 Nouvelles Fonctionnalités v4.0.0

### ✨ Améliorations Majeures

| Fonctionnalité | Ancien Code | Nouveau Code |
|----------------|-------------|--------------|
| **Architecture** | Procédurale, variables globales | POO pure, modèles Pydantic |
| **Concurrence** | Threading (GIL limité) | AsyncIO haute performance |
| **CLI** | Parsing manuel sys.argv | Click moderne avec Rich UI |
| **Dashboard** | ❌ Absent | ✅ FastAPI + WebSocket temps réel |
| **HTTP/2** | ❌ Non supporté | ✅ Support complet avec httpx |
| **Logging** | print() basiques | structlog professionnel |
| **Erreurs** | `except:` nu | Gestion granulaire par type |
| **Validation** | ❌ Absente | Pydantic avec whitelist |
| **Tests** | ❌ Aucun | Structure prête pour pytest |

### 🔒 Safeguards Éducatifs

- **Mode Simulation** : Par défaut, aucune requête réelle n'est envoyée
- **Whitelist obligatoire** : Pour les attaques réelles
- **Token d'autorisation** : Requis en mode production
- **Blocage localhost** : Impossible d'attaquer 127.0.0.1
- **Logs exhaustifs** : Traçabilité complète des actions

---

## 🏗️ Architecture

### Structure du Projet

```
CC-attack/
├── src/
│   ├── __init__.py              # Package principal
│   ├── models.py                # Modèles de données (Pydantic)
│   ├── config.py                # Configuration centralisée
│   ├── logger.py                # Logging structuré
│   ├── proxy_manager.py         # Gestion des proxies
│   ├── request_builder.py       # Construction de requêtes HTTP
│   ├── attack_engine.py         # Moteur d'attaque asyncio
│   ├── cli.py                   # Interface CLI (Click)
│   └── web/
│       ├── app.py               # Application FastAPI
│       ├── templates/           # Templates HTML
│       │   └── index.html
│       └── static/              # Ressources statiques
│           ├── css/style.css
│           └── js/dashboard.js
├── tests/                       # Tests unitaires
├── logs/                        # Fichiers de logs
├── data/                        # Données persistantes
├── proxies/                     # Listes de proxies
├── requirements.txt             # Dépendances Python
├── pyproject.toml              # Configuration packaging
├── .env.example                # Variables d'environnement
└── README_EDU.md               # Ce fichier
```

### Diagramme de Classes

```
┌─────────────────┐
│  AttackConfig   │
│  (Pydantic)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  ProxyManager   │────▶│  ProxyConfig     │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ RequestBuilder  │     │  AttackStats     │
└────────┬────────┘     └─────────▲────────┘
         │                        │
         ▼                        │
┌─────────────────┐              │
│  AttackEngine   │──────────────┘
│  (AsyncIO)      │
└─────────────────┘
```

---

## 💻 Installation

### Prérequis

- Python 3.10 ou supérieur
- pip (gestionnaire de paquets Python)
- Connexion Internet (pour télécharger les proxies)

### Installation Standard

```bash
# 1. Cloner le repository
git clone https://github.com/Leeon123/CC-attack.git
cd CC-attack

# 2. Créer un environnement virtuel (recommandé)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configuration (optionnel)
cp .env.example .env
# Éditer .env selon vos besoins
```

### Installation en Mode Développement

```bash
# Installation éditable avec outils de dev
pip install -e ".[dev]"

# Lancer les tests
pytest tests/ -v --cov=src

# Vérifier le code
black src/ --check
ruff check src/
mypy src/
```

---

## 🎮 Utilisation

### CLI (Interface Ligne de Commande)

#### 1. Télécharger des Proxies

```bash
# Télécharger et valider des proxies SOCKS5
loadtest download --type socks5 --output proxies/socks5.txt --validate

# Télécharger sans validation (plus rapide)
loadtest download --type http --output proxies/http.txt
```

#### 2. Valider des Proxies Existants

```bash
# Valider une liste de proxies
loadtest validate proxies/socks5.txt --type socks5 --timeout 5
```

#### 3. Lancer un Test (Mode Simulation)

```bash
# Test en simulation (AUCUNE requête réelle)
loadtest attack \
    --url https://example.com \
    --mode get \
    --threads 200 \
    --duration 30 \
    --simulation

# Résultat : Statistiques simulées, aucun impact réel
```

#### 4. Lancer un Test Réel (Avec Autorisation)

```bash
# ⚠️ REQUIERT AUTORISATION ÉCRITE
loadtest attack \
    --url https://votre-serveur-de-test.local \
    --mode get \
    --threads 100 \
    --duration 60 \
    --proxy-file proxies/socks5.txt \
    --proxy-type socks5 \
    --real \
    --auth-token VOTRE_TOKEN \
    --whitelist votre-serveur-de-test.local \
    --validate-proxies
```

#### 5. Test HTTP/2

```bash
loadtest attack \
    --url https://example.com \
    --http2 \
    --threads 150 \
    --duration 45 \
    --simulation
```

### Options Disponibles

```
--url, -u           URL cible (requis)
--mode, -m          Mode d'attaque (get/post/head/slow/http2)
--threads, -t       Nombre de threads (défaut: 100)
--duration, -d      Durée en secondes (défaut: 60)
--proxy-file, -f    Fichier de proxies
--proxy-type, -v    Type de proxy (socks4/socks5/http)
--http2             Activer HTTP/2
--simulation        Mode simulation (défaut: activé)
--real              Mode réel (désactive simulation)
--whitelist         Domaines autorisés (multiple)
--auth-token        Token d'autorisation
--validate-proxies  Valider les proxies avant attaque
```

---

## 🌐 Dashboard Web

### Lancement du Dashboard

```bash
# Démarrer le serveur web
loadtest-web

# Ou directement avec uvicorn
uvicorn src.web.app:app --host 127.0.0.1 --port 8080
```

Accédez ensuite à : **http://127.0.0.1:8080**

### Fonctionnalités du Dashboard

1. **Configuration Visuelle**
   - Formulaire interactif pour tous les paramètres
   - Validation en temps réel
   - Prévisualisation de la configuration

2. **Statistiques en Temps Réel**
   - Mise à jour via WebSocket
   - Graphiques Chart.js interactifs
   - Métriques détaillées (RPS, temps de réponse, etc.)

3. **Gestion des Proxies**
   - Téléchargement depuis l'interface
   - Validation automatique
   - Statistiques d'utilisation

4. **Logs en Direct**
   - Événements colorés par type
   - Scroll automatique
   - Export possible

### API REST

#### Endpoints Disponibles

```http
GET  /api/status              # Statut de l'application
POST /api/attack/start        # Démarrer une attaque
POST /api/attack/stop/{id}    # Arrêter une attaque
GET  /api/attack/stats/{id}   # Obtenir les statistiques
GET  /api/sessions            # Lister les sessions actives
POST /api/proxy/download      # Télécharger des proxies
GET  /api/health              # Health check
WS   /ws/{session_id}         # WebSocket temps réel
```

#### Exemple avec cURL

```bash
# Démarrer une attaque
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://example.com",
    "mode": "get",
    "threads": 100,
    "duration": 60,
    "simulation_mode": true
  }'

# Obtenir les statistiques
curl http://localhost:8080/api/attack/stats/SESSION_ID
```

---

## 📝 Exemples

### Exemple 1 : Test de Charge Simple

**Contexte** : Tester la capacité de votre serveur web local.

```bash
# 1. Préparer l'environnement
loadtest download --type http --output proxies.txt

# 2. Lancer le test en simulation d'abord
loadtest attack \
    --url http://localhost:8000 \
    --mode get \
    --threads 50 \
    --duration 30 \
    --simulation

# 3. Si tout est OK, test réel avec autorisation
loadtest attack \
    --url http://localhost:8000 \
    --mode get \
    --threads 50 \
    --duration 30 \
    --real \
    --whitelist localhost
```

### Exemple 2 : Test POST avec Données Custom

**Contexte** : Tester un endpoint API avec payload.

```python
# Créer un fichier data.json
{
    "username": "testuser",
    "password": "testpass123",
    "email": "test@example.com"
}
```

```bash
loadtest attack \
    --url https://api.test.local/register \
    --mode post \
    --data data.json \
    --threads 20 \
    --duration 60 \
    --simulation
```

### Exemple 3 : Test HTTP/2 avec Métriques

```bash
loadtest attack \
    --url https://http2.test.com \
    --http2 \
    --threads 200 \
    --duration 120 \
    --proxy-file proxies/http.txt \
    --validate-proxies \
    --simulation
```

### Exemple 4 : Utilisation Programmatique

```python
import asyncio
from src.models import AttackConfig, AttackMode, ProxyType
from src.attack_engine import AttackEngine
from src.proxy_manager import ProxyManager

async def main():
    # Configuration
    config = AttackConfig(
        target_url="https://example.com",
        mode=AttackMode.GET,
        threads=100,
        duration=60,
        simulation_mode=True,  # Mode sûr
    )

    # Créer le moteur
    engine = AttackEngine(config)

    # Callback pour stats
    def on_stats_update(stats):
        print(f"Requests: {stats.total_requests}, RPS: {stats.requests_per_second:.2f}")

    engine.on_stats_update = on_stats_update

    # Lancer l'attaque
    final_stats = await engine.start()

    # Résultats
    print(f"\nCompleted!")
    print(f"Total requests: {final_stats.total_requests}")
    print(f"Success rate: {final_stats.success_rate:.2f}%")
    print(f"Avg RPS: {final_stats.requests_per_second:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🎓 Objectifs Pédagogiques

### Pour les Étudiants BTS SIO SISR

#### 1. Comprendre les Attaques DDoS Layer 7

**Concepts clés :**
- Différence entre volumétrique (Layer 3/4) et applicatif (Layer 7)
- Techniques de flooding HTTP (GET, POST, Slowloris)
- Rôle des proxies dans la distribution d'attaque

**Exercices :**
1. Analyser le code de `attack_engine.py` pour comprendre le mécanisme
2. Comparer les performances entre HTTP/1.1 et HTTP/2
3. Étudier l'impact du nombre de threads sur les performances

#### 2. Bonnes Pratiques de Développement Python

**Compétences développées :**
- ✅ Architecture orientée objet
- ✅ Programmation asynchrone (asyncio)
- ✅ Validation de données (Pydantic)
- ✅ Gestion d'erreurs granulaire
- ✅ Logging professionnel
- ✅ Tests unitaires

**Exercices :**
1. Ajouter une nouvelle méthode d'attaque dans `models.py`
2. Créer des tests unitaires pour `ProxyManager`
3. Implémenter un nouveau mode d'attaque (ex: WebSocket flood)

#### 3. Sécurité et Pentesting Éthique

**Principes appris :**
- Importance de l'autorisation préalable
- Respect des limites éthiques et légales
- Documentation et reporting de tests
- Mise en place de safeguards

**Exercices :**
1. Rédiger un rapport de pentest après un test autorisé
2. Configurer les whitelists et tokens d'autorisation
3. Analyser les logs pour détecter les anomalies

---

## 🛡️ Comprendre les Défenses Anti-DDoS

### Techniques de Protection

#### 1. Rate Limiting

```python
# Exemple de rate limiter (à ajouter côté serveur)
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

@app.get("/api/endpoint")
@limiter.limit("10/minute")  # Max 10 requêtes par minute
async def endpoint(request: Request):
    return {"message": "success"}
```

**Comment contourner (en test autorisé)** :
- Utiliser des proxies multiples (rotate IP)
- Ralentir le taux d'envoi (slow attack)

#### 2. Challenge-Response (CAPTCHA, Proof-of-Work)

```python
# Exemple de protection par challenge
@app.get("/protected")
async def protected(pow_solution: str):
    if not verify_proof_of_work(pow_solution):
        raise HTTPException(status_code=403, detail="Invalid PoW")
    return {"data": "sensitive"}
```

**Limites de cet outil** :
- Ne peut pas résoudre de CAPTCHAs automatiquement
- PoW ralentit significativement l'attaque

#### 3. Web Application Firewall (WAF)

**Détection par signatures** :
- User-agents suspects
- Patterns de requêtes anormaux
- Fréquence trop élevée depuis une IP

**Contournement (légal uniquement)** :
- Randomisation des user-agents ✅ (implémenté)
- Variation des headers ✅ (implémenté)
- Timing aléatoire (à ajouter)

#### 4. CDN et Caching

**Services comme Cloudflare** :
- Cache les ressources statiques
- Absorbe le trafic malveillant
- Challenge automatique des bots

**Test** :
```bash
# Tester avec et sans cache
loadtest attack --url https://cached-site.com --simulation
# Observer : Très peu d'impact si bien configuré
```

### Exercice Pratique : Défendre un Serveur

**Projet** : Créer un serveur Flask/FastAPI vulnérable puis le sécuriser.

```python
# 1. Serveur vulnérable
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello"}

# 2. Tester avec loadtest
# loadtest attack --url http://localhost:8000 --threads 500

# 3. Ajouter des protections progressivement
# - Rate limiting
# - CAPTCHA après X requêtes
# - Analyse comportementale
```

---

## 🔧 Dépannage

### Problème : "Module not found"

```bash
# Solution : Vérifier l'installation
pip list | grep aiohttp
pip install -r requirements.txt --upgrade
```

### Problème : "No proxies available"

```bash
# Solution : Télécharger et valider
loadtest download --type socks5 --validate
```

### Problème : "Connection timeout"

**Causes possibles :**
1. Proxies morts → Valider la liste
2. Firewall bloque les connexions
3. Target inaccessible

```bash
# Debug
curl -v --socks5 PROXY_IP:PORT https://target.com
```

### Problème : "WebSocket connection failed"

```bash
# Vérifier que le serveur web tourne
curl http://localhost:8080/api/health

# Vérifier les logs
tail -f logs/app.log
```

### Activer les Logs de Debug

```bash
# Via variable d'environnement
export LOG_LEVEL=DEBUG
loadtest attack ...

# Ou dans .env
LOG_LEVEL=DEBUG
```

---

## 📚 Ressources Supplémentaires

### Documentation Technique

- [AsyncIO Python](https://docs.python.org/3/library/asyncio.html)
- [Pydantic](https://docs.pydantic.dev/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [aiohttp](https://docs.aiohttp.org/)

### Sécurité et Pentesting

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [HackTheBox](https://www.hackthebox.com/) - Pratique légale

### Références BTS SIO

- [Référentiel BTS SIO](https://www.sup.adc.education.fr/btslst/referentiel/BTS_SIO_LegrandSebastien.pdf)
- Bloc 2 : Cybersécurité des infrastructures

---

## 👥 Contribution

Pour les étudiants souhaitant contribuer :

1. Fork le projet
2. Créer une branche (`git checkout -b feature/amelioration`)
3. Commit vos changements
4. Push et créer une Pull Request

**Idées de contributions :**
- Ajouter de nouveaux modes d'attaque
- Améliorer le dashboard (graphiques supplémentaires)
- Écrire des tests unitaires
- Traduire la documentation

---

## 📜 Licence et Responsabilité

**Licence** : GNU General Public License v2.0

**Clause de Non-Responsabilité** :

Les auteurs et contributeurs de cet outil déclinent toute responsabilité pour :
- Toute utilisation illégale ou non autorisée
- Dommages causés à des systèmes tiers
- Violations des lois locales ou internationales

L'utilisateur est seul responsable de ses actions et doit :
1. Obtenir une autorisation écrite avant tout test
2. Respecter les lois en vigueur
3. Utiliser l'outil uniquement à des fins éducatives

---

## ✨ Remerciements

- **L330n123** - Auteur du code original
- **Communauté BTS SIO SISR** - Retours et suggestions
- **Contributeurs open-source** - Bibliothèques utilisées

---

## 📞 Support

Pour questions pédagogiques :
- Ouvrir une issue GitHub
- Email : [À configurer]

**Version** : 4.0.0 - Décembre 2024
**Dernière mise à jour** : 25/12/2024
