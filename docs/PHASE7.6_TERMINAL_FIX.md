# Phase 7.6: Terminal Fix & Preview Improvements

**Date**: 2025-12-30
**Status**: In Progress
**Version**: v0.2.4 → v0.2.5

---

## 🎯 Objectif

Résoudre les problèmes critiques du terminal et améliorer la fonctionnalité de prévisualisation:
1. Terminal PTY complètement cassé (pas de prompt, pas d'input)
2. Préparation pour la synchronisation de scroll (structure de base)

---

## 🐛 Problèmes Identifiés

### 1. Terminal PTY Non Fonctionnel
**Symptômes**:
- Pas de prompt `$` affiché
- Impossible de taper des commandes
- Impossible de fermer les onglets terminaux
- Terminal complètement inutilisable

**Causes Probables**:
1. PTY fork réussi mais shell pas initialisé correctement
2. Environnement shell pas configuré (TERM, PS1)
3. Gestion des erreurs insuffisante
4. Path du projet peut ne pas exister

### 2. Scroll Sync Pas Implémenté
**État**: Hook `useSyncScroll` créé mais jamais intégré
**Complexité**: Synchronisation avec Monaco Editor très complexe

---

## ✨ Correctifs Implémentés

### 1. Terminal PTY - Améliorations

#### A. Gestion Robuste du Path
```python
# AVANT - Échoue si path n'existe pas
os.chdir(self.project_path)

# APRÈS - Fallback au home directory
try:
    os.chdir(self.project_path)
except Exception as e:
    # Si le path n'existe pas, utiliser home directory
    os.chdir(os.path.expanduser('~'))
```

#### B. Configuration Environnement Shell
```python
# Variables d'environnement pour meilleure expérience terminal
os.environ['TERM'] = 'xterm-256color'
os.environ['PS1'] = '\\[\\033[1;32m\\]\\u@\\h\\[\\033[00m\\]:\\[\\033[1;34m\\]\\w\\[\\033[00m\\]\\$ '
```

**Avantages**:
- `TERM=xterm-256color`: Support couleurs et features modernes
- `PS1` personnalisé: Prompt coloré user@host:path$
- Prompt visible dès la connexion

#### C. Meilleur Logging/Debugging
```python
# Log succès création session
print(f"Terminal session started: pid={self.pid}, fd={self.master_fd}")

# Traceback complet sur erreur
except Exception as e:
    print(f"Failed to start terminal: {e}")
    import traceback
    traceback.print_exc()
```

### 2. Structure Preview pour Scroll Sync

#### Modification MarkdownPreview.tsx
Transformation en `forwardRef` pour exposer scroll container:

```typescript
// AVANT - Composant simple
export function MarkdownPreview({ content, loading, error }: MarkdownPreviewProps)

// APRÈS - forwardRef avec handle
export const MarkdownPreview = forwardRef<MarkdownPreviewHandle, MarkdownPreviewProps>(
  ({ content, loading, error }, ref) => {
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    useImperativeHandle(ref, () => ({
      getScrollContainer: () => scrollContainerRef.current,
    }));

    // ... rest of component
  }
);
```

**Interface Handle**:
```typescript
export interface MarkdownPreviewHandle {
  getScrollContainer: () => HTMLDivElement | null;
}
```

**Bénéfices**:
- ✅ Structure prête pour scroll sync
- ✅ Ref exposée au parent
- ✅ Pattern React moderne (forwardRef + useImperativeHandle)
- ⏳ Implémentation scroll sync différée (complexité Monaco Editor)

---

## 📊 Modifications de Code

### Backend

**`gathering/workspace/terminal_manager.py`**:
- ✅ Fallback path robuste (home directory si project_path invalide)
- ✅ Variables environnement TERM et PS1 configurées
- ✅ Logging amélioré avec pid et fd
- ✅ Traceback complet sur erreurs

### Frontend

**`dashboard/src/components/workspace/MarkdownPreview.tsx`**:
- ✅ Conversion en forwardRef
- ✅ useImperativeHandle pour exposer scroll container
- ✅ Interface MarkdownPreviewHandle exportée
- ✅ scrollContainerRef créé et attaché

---

## 🧪 Tests Nécessaires

### Terminal PTY
- [ ] Ouvrir terminal → Prompt `$` visible immédiatement
- [ ] Taper `ls` → Commande s'exécute et output affiché
- [ ] Taper `pwd` → Path affiché correctement
- [ ] Couleurs → Prompt coloré (vert/bleu)
- [ ] Multiples onglets → Création/switch/fermeture fonctionnent
- [ ] Fermeture onglet → Session cleanup propre

### Markdown Preview
- [ ] Ouvrir fichier `.md` → Preview s'affiche
- [ ] Éditer contenu → Preview se met à jour
- [ ] Build TypeScript → 0 erreurs

---

## 🚧 Limitations Connues

### Scroll Sync
**Status**: Structure prête mais pas implémenté

**Raisons**:
1. **Monaco Editor Complexité**:
   - Utilise système scroll propriétaire
   - Pas de DOM scroll natif accessible facilement
   - Nécessite API Monaco spécifique

2. **Approches Possibles**:
   - Option A: `editor.onDidScrollChange()` → Sync vers preview
   - Option B: Scroll preview seulement (sans sync editor)
   - Option C: Line-based sync (correspondance lignes code/preview)

3. **Décision**:
   - Phase 7.6: Structure de base (ref exposure)
   - Phase 7.7: Implémentation scroll sync si nécessaire

---

## 📈 Impact

### Terminal
**Avant**: 🔴 Complètement cassé, inutilisable
**Après**: 🟢 Devrait fonctionner normalement

**Améliorations Clés**:
- Prompt affiché
- Commandes exécutables
- Couleurs supportées
- Robustesse erreurs path

### Preview
**Avant**: Fonctionnel mais sans scroll sync
**Après**: Structure prête pour scroll sync futur

---

## 🔍 Debugging Tips

### Terminal Ne Marche Toujours Pas

1. **Check Backend Logs**:
```bash
# Démarrer avec logs verbeux
python3 -m uvicorn gathering.api:app --port 8000

# Dans les logs, chercher:
# "Terminal session started: pid=XXXX, fd=YYYY"
```

2. **Test Import Terminal Manager**:
```bash
python3 -c "from gathering.workspace.terminal_manager import terminal_manager; print('OK')"
```

3. **Check WebSocket Connection**:
```javascript
// Browser console
ws = new WebSocket('ws://localhost:8000/ws/terminal/1')
ws.onopen = () => console.log('Connected!')
ws.onerror = (e) => console.error('Error:', e)
```

4. **Check PTY Disponible**:
```bash
python3 -c "import pty; print('PTY available')"
```

---

## 📁 Fichiers Modifiés

### Backend
1. **`gathering/workspace/terminal_manager.py`**
   - Lignes 28-66: Méthode `start()` améliorée
   - Ajout fallback path, env vars, logging

### Frontend
2. **`dashboard/src/components/workspace/MarkdownPreview.tsx`**
   - Ligne 6: Ajout `forwardRef`, `useImperativeHandle`
   - Lignes 16-18: Interface `MarkdownPreviewHandle`
   - Lignes 20-78: Conversion composant en forwardRef
   - Ligne 23: `scrollContainerRef` créé
   - Lignes 25-27: `useImperativeHandle` implémenté

---

## 🎯 Prochaines Étapes

### Immédiat (Phase 7.6)
- [x] Terminal PTY fixes
- [x] Preview structure pour scroll sync
- [ ] Tests manuels terminal
- [ ] Validation user

### Futur (Phase 7.7 si nécessaire)
- [ ] Implémentation scroll sync Monaco ↔ Preview
- [ ] Options scroll sync (line-based vs pixel-based)
- [ ] Config user (enable/disable sync)

---

## 📝 Notes Techniques

### Pourquoi PS1 Personnalisé?
```bash
# Format: user@host:path$
# Codes couleur ANSI:
\\[\\033[1;32m\\]  # Vert bold pour user@host
\\[\\033[00m\\]    # Reset
\\[\\033[1;34m\\]  # Bleu bold pour path
\\[\\033[00m\\]    # Reset
\\$               # $ symbol
```

### PTY Fork Process
```
Parent Process (Python FastAPI)
    │
    ├─ pty.fork()
    │
    ├─ Child Process (pid=0)
    │  └─ os.execvp(shell)  → Remplacé par bash
    │
    └─ Parent Process (pid>0)
       └─ master_fd → Read/Write terminal I/O
```

---

**Phase 7.6 Status**: Fixes implémentés, tests manuels requis

**User Feedback Needed**:
- ✅ Terminal fonctionne maintenant?
- ✅ Prompt visible?
- ✅ Commandes exécutables?
- ❓ Scroll sync nécessaire pour preview?
