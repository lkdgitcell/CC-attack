# 🚀 Quick Start Guide - HTTP Load Tester EDU

## Installation Rapide (3 minutes)

```bash
# 1. Cloner et entrer dans le dossier
git clone https://github.com/Leeon123/CC-attack.git
cd CC-attack

# 2. Créer environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# OU: venv\Scripts\activate  # Windows

# 3. Installer dépendances
pip install -r requirements.txt

# 4. Copier configuration
cp .env.example .env

# ✅ Installation terminée !
```

---

## 🎯 Premier Test (Mode Sécurisé)

### Option 1 : Interface Web (Recommandé pour débutants)

```bash
# Lancer le dashboard
python web_server.py

# Ouvrir dans le navigateur :
# http://127.0.0.1:8080
```

1. Entrer une URL cible (ex: `https://example.com`)
2. Garder "Simulation Mode" coché ✅
3. Cliquer sur "🚀 Start Attack"
4. Observer les statistiques en temps réel

**Aucune requête réelle n'est envoyée !**

---

### Option 2 : Ligne de Commande

```bash
# Test de simulation simple
python main.py attack \
    --url https://example.com \
    --mode get \
    --threads 100 \
    --duration 30 \
    --simulation
```

---

## 📥 Télécharger des Proxies

### Via Web Dashboard

1. Cliquer sur "📥 Download Proxies"
2. Choisir le type (SOCKS5 recommandé)
3. Attendre le téléchargement

### Via CLI

```bash
# Télécharger et valider automatiquement
python main.py download \
    --type socks5 \
    --output proxies.txt \
    --validate
```

---

## 🧪 Tests Avancés

### Test avec Proxies

```bash
# 1. Télécharger proxies d'abord
python main.py download --type socks5 --validate

# 2. Utiliser dans un test
python main.py attack \
    --url https://example.com \
    --proxy-file proxy.txt \
    --threads 200 \
    --simulation
```

### Test HTTP/2

```bash
python main.py attack \
    --url https://http2.test.com \
    --http2 \
    --threads 150 \
    --simulation
```

---

## ⚠️ Mode Réel (AUTORISATION REQUISE)

**Ne jamais utiliser sans permission écrite !**

```bash
python main.py attack \
    --url https://VOTRE-SERVEUR.local \
    --mode get \
    --threads 100 \
    --duration 60 \
    --real \
    --whitelist VOTRE-SERVEUR.local \
    --auth-token VOTRE_TOKEN
```

Le système vous demandera confirmation.

---

## 🔍 Commandes Utiles

```bash
# Aide générale
python main.py --help

# Aide sur une commande
python main.py attack --help
python main.py download --help

# Version
python main.py --version

# Valider des proxies existants
python main.py validate proxies.txt --type socks5
```

---

## 📊 Exemples de Résultats

### CLI Output

```
╔══════════════════════════════════════════════════════╗
║   HTTP Load Tester - Educational Version 4.0.0      ║
╚══════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────┐
│ Attack Configuration                            │
├─────────────────────────────────────────────────┤
│ Target URL       │ https://example.com          │
│ Mode             │ GET                          │
│ Threads          │ 100                          │
│ Duration         │ 60s                          │
│ Simulation Mode  │ YES (Safe)                   │
└─────────────────────────────────────────────────┘

🚀 Starting attack...

┌─────────────────────────────────────────────────┐
│ Live Statistics                                 │
├─────────────────────────────────────────────────┤
│ Total Requests    │ 15,432                      │
│ Successful        │ 14,678                      │
│ Failed            │ 754                         │
│ Success Rate      │ 95.12%                      │
│ Requests/sec      │ 257.20                      │
│ Avg Response Time │ 12.45ms                     │
└─────────────────────────────────────────────────┘

✓ Attack completed successfully
```

---

## 🆘 Problèmes Courants

### "Module not found"

```bash
# Réinstaller dépendances
pip install -r requirements.txt --upgrade
```

### "Permission denied"

```bash
# Rendre scripts exécutables (Linux/Mac)
chmod +x main.py web_server.py
```

### Port 8080 déjà utilisé

```bash
# Changer le port dans .env
echo "WEB_PORT=8888" >> .env

# Ou directement :
uvicorn src.web.app:app --port 8888
```

### Proxies ne fonctionnent pas

```bash
# Télécharger de nouveaux proxies
python main.py download --type socks5 --validate

# Ou essayer un autre type
python main.py download --type http --validate
```

---

## 📚 Prochaines Étapes

1. ✅ **Lire** le [README_EDU.md](README_EDU.md) complet
2. ✅ **Explorer** le code source dans `src/`
3. ✅ **Tester** différents modes (GET, POST, HEAD)
4. ✅ **Comprendre** les défenses anti-DDoS
5. ✅ **Contribuer** avec de nouvelles features

---

## 🎓 Ressources Pédagogiques

- **Documentation complète** : [README_EDU.md](README_EDU.md)
- **Code source commenté** : `src/` directory
- **Exemples** : Section "Exemples" du README

---

## ⚖️ Rappel Légal

- ✅ Usage éducatif uniquement
- ✅ Autorisation écrite obligatoire pour tests réels
- ❌ Jamais sur des systèmes tiers sans permission

**Vous êtes responsable de vos actions.**

---

**Bon apprentissage ! 🎓**

Version 4.0.0 - BTS SIO SISR Edition
