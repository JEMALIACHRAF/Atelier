# Installation Atelier sur Windows

Guide complet pour utilisateur non-technique. Comptez 15 minutes la première fois.

## Deux modes d'authentification possibles

Atelier détecte automatiquement lequel vous utilisez selon ce qui est dans `.env`:

**Mode Pro OAuth** (défaut, recommandé si vous avez un abonnement Claude Pro ou Max)
Pas de clé API. Vous vous connectez une fois avec `claude login` qui ouvre le navigateur et lie Claude Code à votre compte Claude.ai. Toutes les requêtes tapent votre quota Pro. Simple, pas de facturation à l'usage.

**Mode API** (si vous préférez facturer à l'usage ou router vers Kimi/GPT/Gemini)
Vous mettez `ANTHROPIC_API_KEY=sk-ant-...` dans `.env`. Atelier démarre alors CCR (Claude Code Router) automatiquement en arrière-plan, et route selon la config `.ccr/config.json` (par défaut: Opus pour "think", Kimi pour "background", Gemini pour "longContext").

## Prérequis à installer une fois

### 1. Python 3.11 ou plus récent

Télécharger: https://www.python.org/downloads/

Pendant l'installation, **cochez impérativement la case "Add Python to PATH"** sur le premier écran. Sinon rien ne marchera.

Vérifier dans un terminal (touche Windows, taper `cmd`, entrée):
```
python --version
```
Doit afficher `Python 3.11.x` ou plus.

### 2. Node.js 20 ou plus récent

Télécharger: https://nodejs.org/ (prendre la version LTS, bouton de gauche).

Installer avec toutes les options par défaut.

Vérifier:
```
node --version
```
Doit afficher `v20.x` ou plus.

### 3. (Optionnel) Git

Si vous voulez versionner vos engagements et pouvoir revenir en arrière.

Télécharger: https://git-scm.com/download/win

## Installation d'Atelier

### 1. Dézipper

Dézipper `atelier.zip` dans un dossier facile à retrouver, par exemple `C:\Users\VotreNom\Documents\atelier\`.

Évitez les chemins avec accents ou espaces exotiques.

### 2. Configurer `.env` (optionnel)

Dans le dossier `atelier`, copiez `.env.example` en `.env` (sans extension).

**Mode Pro OAuth**: laissez `ANTHROPIC_API_KEY` vide. Vous pouvez remplir Tavily/Firecrawl/Exa si vous voulez le web search côté Hunter (sinon le Hunter utilise WebSearch/WebFetch natifs de Claude Code).

**Mode API**: remplissez `ANTHROPIC_API_KEY=sk-ant-...` depuis https://console.anthropic.com/. Si vous voulez aussi utiliser Kimi/GPT/Gemini, remplissez les clés correspondantes.

**Choix du modèle** (optionnel, défaut `sonnet`):
```
ATELIER_MODEL=sonnet
```
Valeurs acceptées: `sonnet` (défaut, économique), `opus` (meilleur raisonnement, plus cher en quota), `haiku` (ultra rapide, moins précis).

### 3. Premier lancement

Double-cliquer `start.bat`. Il installe automatiquement:
- `@anthropic-ai/claude-code` (le moteur agent)
- Les dépendances Python (fastapi, uvicorn, pydantic, python-dotenv)

**Important si c'est votre première installation de Claude Code**: après l'installation, `start.bat` vous demandera de faire `claude login` dans un nouveau terminal:

1. Ouvrir un nouveau cmd (touche Windows, taper `cmd`, entrée)
2. Taper `claude login`
3. Le navigateur s'ouvre, se connecter avec votre compte Claude.ai (le même que claude.ai)
4. Retour dans la fenêtre, c'est validé
5. Relancer `start.bat`

Pour le mode API avec routing CCR, installer en plus:
```
npm install -g @musistudio/claude-code-router
```

Au deuxième lancement de `start.bat`, tout va plus vite (5 secondes). Quand vous voyez `Uvicorn running on http://127.0.0.1:7777`, votre navigateur s'ouvre automatiquement sur l'interface Atelier.

## Utilisation quotidienne

À chaque fois que vous voulez utiliser Atelier:
1. Double-cliquer `start.bat`
2. Attendre 5 secondes
3. Le navigateur s'ouvre sur `http://localhost:7777`
4. Vous êtes prête

Pour arrêter: fermer la fenêtre noire (celle du terminal). L'interface web se ferme avec. Si vous étiez en mode API, CCR s'arrête aussi proprement.

## Problèmes fréquents

**"python n'est pas reconnu"**: Python mal installé, refaire l'étape 1 en cochant bien "Add Python to PATH".

**"npm n'est pas reconnu"**: Node.js mal installé, refaire l'étape 2.

**La page ne charge pas**: Attendre 10 secondes de plus. Si toujours rien, regarder la fenêtre noire pour voir le message d'erreur.

**"claude: Please run `claude login`"**: faire exactement ça dans un nouveau terminal.

**Mode API: les requêtes échouent avec 401**: votre `ANTHROPIC_API_KEY` est invalide ou le quota est épuisé. Vérifier sur https://console.anthropic.com/.

**Les agents ne trouvent pas de données en ligne**: il faut au moins une clé parmi Tavily, Firecrawl, Exa. Sinon le Hunter reste limité à ce que Claude connaît déjà et à `WebSearch` natif de Claude Code.

**CCR ne démarre pas**: `npm install -g @musistudio/claude-code-router` d'abord. Si le nom du package a changé, chercher "claude code router" sur npm.

## Mise à jour

Pour mettre à jour Claude Code:
```
npm update -g @anthropic-ai/claude-code
```

Pour mettre à jour CCR (si installé):
```
npm update -g @musistudio/claude-code-router
```

Pour mettre à jour Atelier: je vous enverrai un nouveau zip. Décompresser par-dessus en gardant votre `.env` et votre dossier `workspace/`.

## Pour aller plus loin

Les configurations des agents sont dans `.claude/agents/*.md`. Vous pouvez les modifier à la main pour ajuster leurs prompts, leurs outils autorisés, leurs modèles. Pas besoin de redémarrer, les changements sont pris en compte à la prochaine exécution.

Les règles globales du Chief sont dans `CLAUDE.md` à la racine. Idem, modifiable, pas de redémarrage.

La config routing CCR est dans `.ccr/config.json`. Vous pouvez changer quels modèles sont utilisés pour quelles tâches (think, background, longContext) sans toucher au code.
