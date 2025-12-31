# Quick Hover Test

## Étape 1: Vérifier que le provider est enregistré
✅ FAIT - Vous voyez: `✓ Hover provider registered for python`

## Étape 2: Tester si Monaco déclenche le hover

1. Ouvrir test_pylsp_hover.py dans le workspace
2. **Survoler le mot `sys` à la ligne 2**
3. **Attendre 200ms (debounce)**

### Que devez-vous voir dans la console ?

**Si Monaco déclenche le hover:**
```
[HOVER] Triggered at line 2, col X
[HOVER] Requesting hover for test_pylsp_hover.py at 2:X
[HOVER] Backend response: {contents: {...}}
[HOVER] ✓ Displaying documentation (XXX chars)
```

**Si vous ne voyez PAS `[HOVER] Triggered`:**
→ Monaco ne déclenche pas le hover provider
→ Problème de configuration Monaco

## Étape 3: Forcer Monaco à activer le hover

Si le hover ne se déclenche pas, Monaco a peut-être désactivé le hover par défaut.

### Solutions possibles:

1. **Vérifier les options Monaco dans CodeEditor.tsx**
2. **Maintenir Ctrl/Cmd enfoncé** pendant le survol
3. **Cliquer sur le mot puis survoler**

## Test Alternatif: Autocomplete

L'autocomplete devrait fonctionner car il est déclenché par `.`

Tapez dans l'éditeur:
```python
sys.
```

Vous devriez voir:
- Dropdown avec 84+ suggestions
- Documentation preview dans le dropdown

