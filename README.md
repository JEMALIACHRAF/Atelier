# Atelier v2.3

Boîte de conseil stratégique agentique. Interface web localhost pour utilisateurs non-techniques. Backend FastAPI, frontend HTML + Alpine.js, orchestration par Claude Code + MCP + filesystem partagé.

8 types de mission (étude de marché, benchmark concurrentiel, due diligence M&A, entry strategy, business plan, pricing, operations diagnostic, digital transformation). 9 agents spécialisés dont un Partner Review qui challenge le livrable avant publication. 3 modes de vitesse (Express, Standard, Exhaustif). Upload de documents, révisions à la demande, bouton arrêt, reprise à chaud après crash.

## Vue d'ensemble

```
Vous (navigateur)          http://localhost:7777
        |
        v
  Frontend HTML Alpine    3 vues: dashboard, nouvelle étude (2 étapes), détail
        |
        v
  Backend FastAPI         REST + WebSocket, pilote la fleet, gère les uploads
        |
        v
  Claude Code             Chief orchestrator + agents dispatchés selon mission
        |
        v
  Agents (9)              Framer, Hunter, Analyst, Benchmarker, Risk-Scorer,
                          Strategist, Synthesizer, Producer, Partner Review
        |
        v
  workspace/              Système de fichiers partagé, git-trackable
```

## Installation

Voir `SETUP_WINDOWS.md` pour la procédure détaillée.

Résumé:
1. Installer Python 3.11+ et Node.js 20+
2. Dézipper ce dossier
3. Dans un cmd: `pip install -r requirements.txt` (installe aussi python-pptx, docx, reportlab, matplotlib, pandas, pywin32)
4. Dans un cmd: `claude login` (OAuth Claude Pro, une fois)
5. Double-cliquer `start.bat`
6. Le navigateur s'ouvre sur `http://localhost:7777`

## Modes d'authentification

Détection automatique selon `.env`:

- **Mode Pro OAuth** (défaut): pas de clé API, authentification via `claude login`. Toutes les requêtes tapent votre quota Pro.
- **Mode API**: avec `ANTHROPIC_API_KEY=sk-ant-...` dans `.env`, Atelier démarre automatiquement CCR en arrière-plan pour router entre Opus/Sonnet/Haiku/Kimi/GPT/Gemini selon `.ccr/config.json`.

## Configuration modèle

Variable d'env `ATELIER_MODEL` dans `.env` (défaut: `sonnet`):

- `sonnet`: économise votre quota Pro vs Opus par défaut. Recommandé.
- `opus`: meilleur raisonnement, consomme vite votre quota.
- `haiku`: ultra rapide, moins bon.

## Les 9 agents

| Agent | Rôle | Modèle recommandé | Sortie principale |
|-------|------|-------------------|-------------------|
| Framer | Scoping MECE, hypothesis tree, workplan | Opus | `01_workplan.md` |
| Hunter | Data acquisition autonome (web, APIs, uploads) | Sonnet | `02_data/sources.json` |
| Analyst | Market sizing, benchmarks, charts matplotlib | Sonnet | `03_charts/` + `04_models/` |
| Benchmarker | Scoring concurrentiel 0-3 par dimension | Sonnet | `04_models/benchmark_matrix.*` |
| Risk-Scorer | Red flags severité x probabilité pour DD M&A | Opus | `04_models/risk_matrix.*` |
| Strategist | 3 options stratégiques évaluées + reco tranchée | Opus | `04_models/strategic_options.md` |
| Synthesizer | Insights, pyramid principle, verdicts hypothèses | Opus | `05_synthesis.md` |
| Producer | Génère .pptx/.docx/.pdf via python-pptx/docx/reportlab | Sonnet | `06_deliverables/*` |
| Partner Review | Challenge livrable, demande rerolls ciblés | Opus | `07_partner_review.md` |
| Chief | Orchestration + QA + validation | Vous + Claude Code | `decisions/*` |

## Les 8 missions

| Mission | Agents actifs | Durée Standard | Cas d'usage |
|---------|---------------|----------------|-------------|
| Étude de marché | framer, hunter, analyst, synthesizer, producer, partner_review | ~45 min | Cartographie marché, sizing, projections |
| Benchmark concurrentiel | framer, hunter, benchmarker, synthesizer, producer, partner_review | ~35 min | Positionnement vs concurrents |
| Due diligence M&A | framer, hunter, analyst, risk_scorer, synthesizer, producer, partner_review | ~50 min | Red flags cible, questions management |
| Entry strategy | framer, hunter, analyst, strategist, synthesizer, producer, partner_review | ~45 min | Entrée marché / géo / segment |
| Business plan | framer, hunter, analyst, strategist, synthesizer, producer, partner_review | ~50 min | Trajectoire 3-5 ans, leviers croissance |
| Pricing strategy | framer, hunter, analyst, strategist, synthesizer, producer, partner_review | ~40 min | Architecture pricing, impact |
| Operations diagnostic | framer, hunter, analyst, synthesizer, producer, partner_review | ~45 min | Leviers coût/qualité/délai |
| Digital transformation | framer, hunter, analyst, strategist, synthesizer, producer, partner_review | ~50 min | Maturité + roadmap transformation |

Les templates sont dans `templates/missions/*.yaml`, éditables.

## Les 3 speed modes

Choisis au moment de créer une étude:

- **Express** (10-20 min): scope réduit (max 8 hypothèses, 20 datapoints, 10 slides). Pré-brief, pas livrable final.
- **Standard** (30-60 min): calibrage normal, qualité consultant solide.
- **Exhaustif** (60-100 min): scope maximal, sujets structurants.

Les contraintes sont transmises automatiquement à chaque agent via le prompt du Chief.

## Workspace

Chaque engagement est un dossier auto-contenu dans `workspace/engagements/{slug}/`:

```
engagements/2026-10-24_mon-etude/
├── 00_brief.md                 # Brief utilisateur + paramètres mission
├── _meta.json                  # Mission type, speed mode, deliverables demandés
├── _attachments/               # Documents uploadés par l'utilisateur
├── 01_workplan.md              # Framer
├── 02_data/
│   ├── sources.json            # Catalog des sources (Hunter)
│   └── raw/                    # Fichiers bruts fetchés
├── 03_charts/                  # PNG générés (Analyst / Benchmarker)
├── 04_models/                  # Scripts Python, xlsx, rapports agent
├── 05_synthesis.md             # Synthesizer
├── 06_deliverables/            # LIVRABLES FINAUX .pptx .docx .pdf
├── 07_partner_review.md        # Verdict QA interne
├── _log.md                     # Journal technique
├── _raw_claude.log             # Debug stdout brut CLI
└── _revision_request.md        # (optionnel) Demande utilisateur post-livraison
```

## Fonctionnalités UI

- **Dashboard**: cartes En cours / À lancer / Terminées. Statut business-friendly.
- **Nouvelle étude**: 2 écrans (choix mission → formulaire + brief + upload drag & drop).
- **Détail**: 4 onglets (Brief, Livrables téléchargeables, Documents joints, Avancé pour debug).
- **Boutons action**: Lancer, Arrêter, Reprendre, Demander une révision.
- **Progression visuelle**: barre d'étapes nommées en langage métier.

## Trade-offs assumés en v2.3

- Localhost single-user. Multi-user demanderait auth + base utilisateurs.
- Autonomie limitée par votre PC qui doit être allumé pendant les runs.
- Pas de parallélisation réelle entre agents (le workflow est séquentiel).
- Les skills pré-installées Claude.ai (pptx/docx/pdf) ne sont PAS disponibles dans Claude Code. Producer utilise python-pptx, python-docx, reportlab directement.
- MCP servers externes (Tavily, Firecrawl, Exa) désactivés par défaut. Activables en renommant `.mcp.json.example`.

## Dépendances principales

### Python (requirements.txt)
- fastapi, uvicorn, pydantic, python-multipart, python-dotenv, PyYAML
- python-pptx, python-docx, openpyxl, reportlab, Pillow
- matplotlib, pandas, pdfplumber
- pywin32 (Windows uniquement, pour export PowerPoint via COM)

### Node
- `@anthropic-ai/claude-code` installé globalement via `start.bat`

### Optionnel
- `@musistudio/claude-code-router` si mode API avec routing multi-provider

## Faire évoluer

- **Prompts des agents**: `.claude/agents/*.md`, markdown avec frontmatter YAML. Modifiables à chaud.
- **Règles du Chief**: `CLAUDE.md` à la racine.
- **Templates de mission**: `templates/missions/*.yaml`. Ajoutez vos propres cas d'usage.
- **Permissions**: `.claude/settings.json` liste les tools autorisés.
- **Router modèles**: `.ccr/config.json` si mode API.

## Historique des versions

- **v1.0** (oct 2026): Pipeline de base, UI technique avec journal en direct.
- **v2.0** (oct 2026): UI SaaS refaite, upload documents, 8 templates missions (dormants).
- **v2.1-2.2**: 4 nouveaux agents (Benchmarker, Risk-Scorer, Strategist, Partner Review), speed modes, révisions depuis l'UI.
- **v2.3**: Bouton Arrêter, flag --model configurable, deps Python Producer.
