# Rapport d'Audit de Sécurité - GatheRing

**Date:** 2025-12-23
**Version auditée:** 0.1.1
**Auditeur:** Claude Opus 4.5

---

## Résumé Exécutif

Cet audit a identifié et corrigé plusieurs vulnérabilités de sécurité dans le projet GatheRing. Les corrections apportées incluent la mise à jour des dépendances, l'ajout d'un système d'authentification JWT, la sécurisation de l'exécution de code, et l'implémentation de middlewares de protection.

### Score Global

| Catégorie | Avant | Après |
|-----------|-------|-------|
| **Sécurité** | 5/10 | **8/10** |
| **Tests** | 238 passants | **327 passants** |
| **Couverture** | 17% | **33%** |

---

## Vulnérabilités Corrigées

### 1. Injection de Commandes (CRITIQUE)

**Fichier:** `gathering/skills/shell/executor.py`

**Problème:** Utilisation de `shell=True` dans `subprocess.run()` permettant l'injection de commandes.

**Correction:**
```python
# Avant (vulnérable)
result = subprocess.run(command, shell=True, ...)

# Après (sécurisé)
cmd_args = shlex.split(command)
result = subprocess.run(cmd_args, shell=False, ...)
```

### 2. Évaluation de Code Non Sécurisée (CRITIQUE)

**Fichier:** `gathering/skills/code/executor.py`

**Problème:** Utilisation de `eval()` même avec des builtins restreints.

**Correction:** Remplacement par une évaluation AST pure qui n'exécute jamais de code arbitraire.

```python
# Avant (vulnérable)
result = eval(expression, {"__builtins__": safe_builtins}, {})

# Après (sécurisé)
tree = ast.parse(expression, mode='eval')
result = safe_eval_node(tree)  # Évaluation AST récursive
```

### 3. Absence d'Authentification (ÉLEVÉ)

**Problème:** Tous les endpoints API étaient accessibles sans authentification.

**Correction:** Implémentation d'un système JWT complet avec:
- Authentification admin via variables d'environnement
- Authentification utilisateurs via base de données
- Middleware de protection automatique

### 4. CORS Permissif (MOYEN)

**Fichier:** `gathering/api/main.py`

**Problème:** `allow_origins=["*"]` permettait les requêtes de n'importe quelle origine.

**Correction:**
```python
# Configuration restrictive basée sur settings
allow_origins=settings.cors_origins_list  # Liste explicite
allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
allow_headers=["Authorization", "Content-Type", "X-Request-ID"]
```

### 5. Dépendances Obsolètes (MOYEN)

**Problème:** Versions très anciennes des packages LLM.

**Correction:**
| Package | Avant | Après |
|---------|-------|-------|
| anthropic | >=0.15.0 | >=0.35,<1.0 |
| openai | >=1.0 | >=1.30,<2.0 |
| ollama | >=0.1.0 | >=0.3,<1.0 |

---

## Nouvelles Fonctionnalités de Sécurité

### Authentification JWT

**Fichiers créés:**
- `gathering/api/auth.py` - Module d'authentification
- `gathering/api/routers/auth.py` - Endpoints d'authentification

**Endpoints:**
| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/auth/login` | POST | Login OAuth2 (form) |
| `/auth/login/json` | POST | Login JSON |
| `/auth/register` | POST | Inscription utilisateur |
| `/auth/me` | GET | Info utilisateur courant |
| `/auth/verify` | POST | Vérification token |

**Configuration (.env):**
```bash
SECRET_KEY=<clé-secrète-32-bytes>
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD_HASH=<hash-bcrypt>
```

**Génération du hash admin:**
```bash
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('votre-mot-de-passe'))"
```

### Middlewares de Sécurité

**Fichier:** `gathering/api/middleware.py`

#### AuthenticationMiddleware
Protège automatiquement tous les endpoints sauf:
- `/` - Info API
- `/health/*` - Health checks
- `/auth/login`, `/auth/register` - Authentification
- `/docs`, `/redoc`, `/openapi.json` - Documentation

#### RateLimitMiddleware
- Limite configurable (défaut: 60 req/min par IP)
- Headers de réponse: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Bypass pour `/health/*`

#### SecurityHeadersMiddleware
Ajoute les headers de sécurité à toutes les réponses:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Cache-Control: no-store, no-cache, must-revalidate
```

#### RequestLoggingMiddleware
- Log toutes les requêtes avec timing
- Ajout de `X-Request-ID` pour le tracing
- Redaction automatique des données sensibles

---

## Dépendances Ajoutées

### Base de Données
```
sqlalchemy>=2.0,<3.0
asyncpg>=0.29.0,<1.0
psycopg2-binary>=2.9,<3.0
pgvector>=0.3.0,<1.0
alembic>=1.13,<2.0
```

### Authentification
```
python-jose[cryptography]>=3.3,<4.0
passlib[bcrypt]>=1.7,<2.0
bcrypt>=4.0,<5.0
email-validator>=2.0,<3.0
```

---

## Tests Ajoutés

### Tests d'Authentification (`tests/test_auth.py`)
- 31 tests couvrant:
  - Hashing de mots de passe
  - Création/validation de tokens JWT
  - Authentification admin
  - Endpoints d'authentification

### Tests de Middlewares (`tests/test_middleware.py`)
- 24 tests couvrant:
  - Détection des chemins publics
  - Middleware d'authentification
  - Rate limiting
  - Headers de sécurité

### Tests du Code Executor (`tests/test_code_executor.py`)
- 34 tests couvrant:
  - Évaluation d'expressions sûres
  - Blocage des imports dangereux
  - Blocage de exec/eval/open
  - Validation des entrées

---

## Recommandations Futures

### Priorité Haute
1. **Augmenter la couverture de tests à 60%+**
2. **Ajouter des tests d'intégration e2e**
3. **Implémenter le refresh token** pour une meilleure expérience utilisateur

### Priorité Moyenne
4. **Ajouter un audit logging** pour tracer les actions sensibles
5. **Implémenter HTTPS enforcement** en production
6. **Ajouter des tests de performance/charge**

### Priorité Basse
7. **Considérer OAuth2/OIDC** pour l'authentification externe
8. **Ajouter le support 2FA** pour les comptes admin
9. **Implémenter un WAF** (Web Application Firewall)

---

## Configuration de Production

### Variables d'Environnement Requises

```bash
# Obligatoires
SECRET_KEY=<générer avec: python -c "import secrets; print(secrets.token_hex(32))">
ADMIN_EMAIL=admin@votre-domaine.com
ADMIN_PASSWORD_HASH=<hash bcrypt>
DATABASE_URL=postgresql://user:pass@host:5432/gathering

# Recommandées
GATHERING_ENV=production
DEBUG=false
CORS_ORIGINS=https://votre-domaine.com
RATE_LIMIT_PER_MINUTE=60
```

### Checklist de Déploiement

- [ ] `SECRET_KEY` généré et unique
- [ ] `ADMIN_PASSWORD_HASH` défini avec un mot de passe fort
- [ ] `DEBUG=false`
- [ ] `CORS_ORIGINS` configuré avec les domaines autorisés
- [ ] HTTPS activé (via reverse proxy)
- [ ] Base de données PostgreSQL configurée
- [ ] Logs configurés vers un système centralisé

---

## Conclusion

L'audit a permis d'identifier et de corriger les principales vulnérabilités de sécurité du projet. Le système est maintenant protégé par:

1. **Authentification JWT** sur tous les endpoints sensibles
2. **Rate limiting** contre les attaques par force brute
3. **Headers de sécurité** contre les attaques web courantes
4. **Sandbox AST** pour l'exécution de code
5. **Exécution de commandes sécurisée** sans shell

Le projet nécessite encore des améliorations pour atteindre un niveau de sécurité production, notamment l'augmentation de la couverture de tests et l'ajout de fonctionnalités comme le refresh token et l'audit logging.
