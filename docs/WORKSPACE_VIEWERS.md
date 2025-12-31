# 📁 Workspace File Viewers - Phase 7.7

## 🎨 Visualiseurs de Fichiers Multimédias

Le workspace IDE supporte maintenant plusieurs types de fichiers avec des visualiseurs dédiés en mode split-screen.

### Types de Fichiers Supportés

#### 1. **Images** 🖼️
**Extensions**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`

**Fonctionnalités**:
- ✅ Zoom (25% à 400%)
- ✅ Rotation (90°, 180°, 270°)
- ✅ Reset position
- ✅ Téléchargement
- ✅ Affichage plein écran (pas d'éditeur)
- ✅ Pixelation automatique au-delà de 200% zoom

**Preview**: [ImagePreview.tsx](../dashboard/src/components/workspace/ImagePreview.tsx)

#### 2. **JSON** 📋
**Extensions**: `.json`

**Fonctionnalités**:
- ✅ Syntax highlighting avec couleurs
  - 🟣 Clés (purple)
  - 🟢 Strings (green)
  - 🟡 Numbers (amber)
  - 🔵 Booleans (cyan)
  - 🔴 Null (red)
- ✅ Auto-formatting (indentation)
- ✅ Copy to clipboard
- ✅ Collapse/Expand (à venir)
- ✅ Validation + error display

**Preview**: [JSONPreview.tsx](../dashboard/src/components/workspace/JSONPreview.tsx)

#### 3. **CSV/TSV** 📊
**Extensions**: `.csv`, `.tsv`

**Fonctionnalités**:
- ✅ Affichage en tableau formaté
- ✅ Compteur lignes × colonnes
- ✅ Sélecteur de délimiteur
  - Comma (`,`)
  - Semicolon (`;`)
  - Tab (`\t`)
  - Pipe (`|`)
- ✅ Recherche dans toutes les cellules
- ✅ Export CSV
- ✅ Numérotation des lignes
- ✅ Headers sticky

**Preview**: [CSVPreview.tsx](../dashboard/src/components/workspace/CSVPreview.tsx)

#### 4. **Markdown** 📝
**Extensions**: `.md`

**Fonctionnalités**:
- ✅ Preview HTML live
- ✅ Syntax highlighting code blocks
- ✅ Support GFM (GitHub Flavored Markdown)
- ✅ Split-screen éditeur/preview
- ⚠️ Scroll sync désactivé temporairement

**Preview**: [MarkdownPreview.tsx](../dashboard/src/components/workspace/MarkdownPreview.tsx)

#### 5. **HTML** 🌐
**Extensions**: `.html`, `.htm`

**Fonctionnalités**:
- ✅ Rendu iframe sandboxé
- ✅ Reload manuel
- ✅ Split-screen éditeur/preview
- ✅ Affichage isolé (sandbox)

**Preview**: [HTMLPreview.tsx](../dashboard/src/components/workspace/HTMLPreview.tsx)

#### 6. **Python** 🐍
**Extensions**: `.py`

**Fonctionnalités**:
- ✅ Exécution dans environnement sandboxé
- ✅ Capture stdout/stderr
- ✅ Code de sortie
- ✅ Temps d'exécution
- ✅ Timeout 30s
- ✅ Layout optimisé (65% code / 35% sortie)

**Preview**: [PythonRunner.tsx](../dashboard/src/components/workspace/PythonRunner.tsx)

## 🎯 Détection Automatique

Le workspace détecte automatiquement le type de fichier et affiche le viewer approprié :

```typescript
const ext = selectedFile?.toLowerCase() || '';

// Auto-detection
const isMarkdownFile = ext.endsWith('.md');
const isHTMLFile = ext.endsWith('.html') || ext.endsWith('.htm');
const isPythonFile = ext.endsWith('.py');
const isJSONFile = ext.endsWith('.json');
const isCSVFile = ext.endsWith('.csv') || ext.endsWith('.tsv');
const isImageFile = ext.endsWith('.png') || ext.endsWith('.jpg') || ...;
```

## 🔄 Layout Adaptatif

### Split-Screen Standard (50/50)
- Markdown
- HTML
- JSON
- CSV

### Split-Screen Optimisé (65/35)
- Python (plus d'espace pour le code)

### Plein Écran Preview (0/100)
- Images (pas besoin d'éditeur)

## 🎨 Design System

Tous les viewers suivent le **Web3 Dark Theme**:
- 🌌 Background: gradient from slate-900 via purple-900/10
- 🪟 Glass cards avec blur effects
- 🎨 Color scheme cohérent:
  - Purple: Actions principales
  - Cyan: Actions secondaires
  - Green: Succès / Export
  - Amber: Warning / Info
  - Red: Erreurs

## 📦 Structure des Composants

```
dashboard/src/components/workspace/
├── ImagePreview.tsx      # Viewer images avec zoom/rotate
├── JSONPreview.tsx       # Pretty-print JSON avec highlighting
├── CSVPreview.tsx        # Table view avec search
├── MarkdownPreview.tsx   # Rendu markdown (existant)
├── HTMLPreview.tsx       # Iframe preview (existant)
└── PythonRunner.tsx      # Exécuteur Python (existant)
```

## 🚀 Utilisation

1. **Ouvrir un projet** dans le workspace
2. **Sélectionner un fichier** dans le File Explorer
3. **Le viewer approprié s'affiche automatiquement**
4. **Bouton Preview** permet de toggle on/off

## 🔮 Prochaines Améliorations

- [ ] **PDF Viewer** avec `react-pdf`
- [ ] **Video Player** (.mp4, .webm)
- [ ] **Audio Player** (.mp3, .wav, .ogg)
- [ ] **Diff Viewer** pour comparer versions
- [ ] **Notebook Viewer** (.ipynb) Jupyter
- [ ] **XML/YAML** avec syntax highlighting
- [ ] **Logs Viewer** avec filtrage temps réel

## 📊 Statistiques

- **6 types de fichiers** supportés nativement
- **~15 extensions** reconnues
- **3 nouveaux composants** (Image, JSON, CSV)
- **+300 lignes** de code ajoutées
- **0 dépendances** externes supplémentaires

---

**Date**: 2025-12-30
**Version**: Phase 7.7
**Status**: ✅ Completed & Deployed
