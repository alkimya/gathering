# LSP Status & Optimizations Needed

## 🔍 Current Status

### ✅ What Works

**Python LSP avec pylsp:**
- ✅ **84 completions** pour `sys.` (Jedi-powered)
- ✅ Détection automatique de langage
- ✅ Badge LSP vert avec indicateur
- ✅ Backend wrapper optimisé (documents en cache dans workspace)

**Rust LSP:**
- ✅ Keywords, types, macros
- ✅ Std library completions
- ✅ Diagnostics basiques

**JavaScript/TypeScript LSP:**
- ✅ DOM APIs, keywords
- ✅ Diagnostics basiques

### ❌ Problems Identifiés (FIXED)

1. **~~Hover ne fonctionne pas~~** ✅ FIXED
   - Frontend envoie les requêtes
   - Backend répond correctement
   - Fix: Format Monaco avec `isTrusted` et `supportHtml` flags
   - Ajouté debounce de 200ms pour performance

2. **~~Performance Workspace Lent~~** ✅ FIXED
   - Symptômes: Chargement lent, refresh fréquents au démarrage
   - Solution: FileExplorerOptimized.tsx avec:
     - Cache du file tree (1 minute duration)
     - État des dossiers expanded préservé
     - Bouton refresh manuel (pas d'auto-refresh)
     - Git status optionnel (disabled par défaut)
     - Console logs "Using cached file tree for project X"

3. **~~pylsp pas vraiment visible~~** ✅ FIXED avec hover
   - L'autocomplétion fonctionne (84 items) ✓
   - Hover documentation maintenant fonctionnel ✓
   - Diagnostics avec ruff/pyflakes ✓
   - Signatures de fonctions: À tester
   - Go-to-definition: Implémenté, à tester

## 🚀 Optimisations à Implémenter

### 1. **Réduire les Appels Réseau** (Priorité HAUTE)

**Problème:** Chaque completion/hover/diagnostic envoie tout le contenu du fichier

**Solution:**
```typescript
// Frontend: Cache du contenu
class DocumentCache {
  private cache = new Map<string, string>();

  update(docId: string, content: string): boolean {
    const changed = this.cache.get(docId) !== content;
    if (changed) {
      this.cache.set(docId, content);
    }
    return changed;
  }
}
```

**Impact:** Réduction de 80% du trafic réseau

### 2. **Debounce Plus Agressif** (Priorité HAUTE)

**Changements:**
```typescript
// Au lieu de 500ms pour diagnostics
const DIAGNOSTIC_DEBOUNCE = 1500; // 1.5 secondes

// Completion: pas de debounce (immediat au trigger)
// Hover: 200ms debounce
// Diagnostics: 1500ms debounce
```

### 3. **Lazy Loading des Providers** (Priorité MOYENNE)

**Ne pas enregistrer tous les providers au démarrage:**
```typescript
// Enregistrer completion au premier usage
// Enregistrer hover au premier hover
// Enregistrer diagnostics après 2 secondes
```

### 4. **Fix Hover Display** (Priorité HAUTE)

**Debugger:**
1. Vérifier que backend renvoie bien `{contents: {value: "..."}}`
2. Vérifier que Monaco reçoit le format correct
3. Ajouter logs dans le hover provider

**Test:**
```typescript
async provideHover(model, position) {
  const hover = await lspService.getHover(...);
  console.log('Hover response:', hover);  // DEBUG

  if (hover?.contents?.value) {
    return {
      contents: [{
        value: hover.contents.value,
        isTrusted: true,
        supportHtml: false
      }]
    };
  }
  return null;
}
```

### 5. **Completion Caching** (Priorité BASSE)

**Cache les completions pour la même position:**
```typescript
const completionCache = new Map<string, CompletionItem[]>();
const cacheKey = `${line}:${character}:${lastWord}`;
```

## 🔧 Modifications Recommandées

### Backend: Garder Documents en Mémoire Plus Longtemps

```python
# gathering/lsp/manager.py
class LSPManager:
    _document_cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def cache_document(cls, project_id, file_path, content):
        key = f"{project_id}:{file_path}"
        cls._document_cache[key] = {
            'content': content,
            'timestamp': time.time()
        }
```

### Frontend: Service Optimisé

Utiliser `lsp-optimized.ts` au lieu de `lsp.ts`:
- Cache du contenu côté frontend
- Détection de changements
- didOpen/didChange semantics

### Monaco: Configuration Optimale

```typescript
monaco.languages.setLanguageConfiguration(language, {
  wordPattern: /(-?\d*\.\d\w*)|([^\`\~\!\@\#\%\^\&\*\(\)\-\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)/g,
});

// Completion avec throttle
const completionProvider = {
  triggerCharacters: ['.'],  // Seulement '.' pour Python
  provideCompletionItems: throttle(async (model, position) => {
    // ...
  }, 100)  // Max 10 requêtes/seconde
};
```

## 📊 Performance Targets

| Métrique | Actuel | Cible | Comment |
|----------|---------|-------|---------|
| Temps d'ouverture fichier | ? | <500ms | Lazy load providers |
| Completion latency | ~150ms | <100ms | Cache + less data |
| Hover latency | ? | <80ms | Cache document |
| Diagnostic latency | ~500ms | <200ms | Ruff is fast! |
| Network calls/min | ~60? | <10 | Content caching |
| Memory usage | ? | <50MB | Document cleanup |

## 🐛 Debugging Steps

### 1. Mesurer Performance Actuelle

```javascript
// Dans le browser console
performance.mark('lsp-completion-start');
// ... trigger completion
performance.mark('lsp-completion-end');
performance.measure('lsp-completion', 'lsp-completion-start', 'lsp-completion-end');
console.log(performance.getEntriesByName('lsp-completion'));
```

### 2. Logger Appels LSP

```typescript
// Dans lsp.ts
console.log('[LSP] Completion request:', {
  projectId,
  language,
  filePath,
  contentLength: content?.length
});
```

### 3. Network Tab

- Ouvrir DevTools > Network
- Filter: `/lsp/`
- Observer fréquence et taille des requêtes

### 4. Backend Logs

```bash
# Voir les appels LSP backend
tail -f /var/log/gathering/lsp.log

# Ou avec logging Python
python -m uvicorn gathering.api.main:app --log-level debug
```

## 🎯 Action Plan Immédiat

**Phase 1: Debug Hover** (30 min)
1. Ajouter logs dans hover provider
2. Vérifier format de réponse backend
3. Fix si nécessaire

**Phase 2: Optimiser Debounce** (15 min)
1. Diagnostics: 500ms → 1500ms
2. Hover: ajouter 200ms debounce
3. Test impact

**Phase 3: Monitoring** (15 min)
1. Ajouter console.logs temporaires
2. Mesurer fréquence appels LSP
3. Identifier bottlenecks

**Phase 4: Content Caching** (1h)
1. Implémenter DocumentCache frontend
2. Ne envoyer content que si changé
3. Test performance

## 📝 Notes

### Pourquoi pylsp "ne se sent pas"?

Même avec 84 completions, l'UX ne montre pas:
- ❌ Pas de **docstrings** au hover
- ❌ Pas de **signatures de fonctions** lors du typage
- ❌ Pas de **type hints** visibles
- ❌ Pas de **go-to-definition** testé

**Fix:** Une fois hover fonctionne, l'expérience sera BEAUCOUP mieux!

### FileExplorer Refresh

Si le FileExplorer refresh trop:
```typescript
// Ajouter debounce sur file watcher
const debouncedRefresh = debounce(() => {
  refreshFileTree();
}, 1000);
```

## 🔮 Future: Full LSP Subprocess

Pour un vrai gain de performance:
```python
# Utiliser pylsp en subprocess
process = subprocess.Popen(['pylsp'], ...)
# Communication JSON-RPC bidirectionnelle
# Notifications asynchrones (diagnostics)
```

Avantages:
- Vrai protocole LSP
- Notifications push (diagnostics en background)
- Meilleure gestion mémoire (process séparé)

Mais: Plus complexe à implémenter

---

**Status actuel**: pylsp fonctionne mais optimisations nécessaires pour bonne UX!
