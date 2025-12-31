# Debug: Monaco ne déclenche pas le hover

## Symptôme
- ✅ Provider enregistré: `✓ Hover provider registered for python`
- ❌ Pas de log `[HOVER] Triggered` quand on survole
- ❌ Pas de tooltip

→ **Monaco ne déclenche pas `provideHover()`**

## Tests à faire

### Test 1: Forcer le hover avec raccourci clavier
1. Placer le curseur sur le mot `sys`
2. Appuyer sur **Ctrl+K Ctrl+I** (Windows/Linux) ou **Cmd+K Cmd+I** (Mac)
3. Cela devrait forcer l'affichage du hover

**Résultat attendu:**
- Console: `[HOVER] Triggered`
- Tooltip apparaît

### Test 2: Vérifier l'autocomplete
1. Taper `sys.` sur une nouvelle ligne
2. L'autocomplete devrait fonctionner (déclenché par `.`)

**Résultat attendu:**
- Dropdown avec suggestions
- Pas besoin de hover pour ça

### Test 3: Vérifier que Monaco est en mode "édition"
Le hover peut ne pas fonctionner si:
- L'éditeur est en "read-only"
- Le focus n'est pas dans l'éditeur
- Une autre extension Monaco bloque

## Hypothèses

### Hypothèse 1: Monaco version/configuration
Monaco Editor peut avoir des comportements différents selon:
- Version de @monaco-editor/react
- Configuration par défaut

### Hypothèse 2: Conflit avec hover natif
Monaco a peut-être son propre hover qui bloque le nôtre.

### Hypothèse 3: Timing
Le provider est peut-être enregistré APRÈS que Monaco soit monté,
et Monaco ne rafraîchit pas sa liste de providers.

## Solutions à tester

### Solution 1: Enregistrer le provider différemment
Au lieu de `registerHoverProvider`, essayer avec `onDidCreateModel`.

### Solution 2: Vérifier la version Monaco
```bash
cd dashboard
npm list monaco-editor @monaco-editor/react
```

### Solution 3: Mode debug Monaco
Ajouter dans CodeEditor options:
```typescript
options={{
  // ... autres options
  parameterHints: { enabled: true },
  suggest: {
    showWords: true,
    showSnippets: true,
  },
}}
```

## Prochaine étape

Essayons de vérifier si le provider est vraiment enregistré côté Monaco:

```typescript
// Dans LSPCodeEditor après registerHoverProvider
const providers = monaco.languages.getLanguages();
console.log('Registered languages:', providers);

// Vérifier les providers pour python
const pythonProviders = (monaco.languages as any)._providers?.get('python');
console.log('Python providers:', pythonProviders);
```
