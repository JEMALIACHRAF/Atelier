<div align="center">

<h1>Atelier</h1>

<p><strong>Boutique de conseil stratégique agentique.</strong><br/>
Des agents LLM collaborent pour produire des études de marché, benchmarks, due diligences et plans stratégiques<br/>de niveau junior/senior consultant, à partir d'un brief et de documents.</p>

<p>
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-blue?style=flat-square"/>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img alt="Node" src="https://img.shields.io/badge/node-20+-339933?style=flat-square&logo=node.js&logoColor=white"/>
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img alt="Alpine.js" src="https://img.shields.io/badge/Alpine.js-3.13-8BC0D0?style=flat-square&logo=alpine.js&logoColor=white"/>
  <img alt="Claude Code" src="https://img.shields.io/badge/powered%20by-Claude%20Code-D97757?style=flat-square"/>
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green?style=flat-square"/>
</p>

<p>
  <a href="#quick-start">Quick Start</a> ·
  <a href="#features">Features</a> ·
  <a href="#how-it-works">Architecture</a> ·
  <a href="#mission-templates">Missions</a> ·
  <a href="#deliverables">Livrables</a> ·
  <a href="#roadmap">Roadmap</a>
</p>

</div>

---

## Pourquoi Atelier

Les systèmes agentiques publics se limitent souvent au chatbot ou au data pipeline. Atelier démontre un cas d'usage plus ambitieux: **reproduire le workflow d'une boîte de conseil stratégique de bout en bout**, avec cadrage, collecte, analyse, synthèse, livrables PowerPoint/Word/PDF et QA interne par un agent "partner review".

L'utilisateur décrit un sujet, choisit un type de mission (étude de marché, due diligence, benchmark, entry strategy...), ajoute éventuellement des documents, et récupère 30 à 90 minutes plus tard des livrables sourcés, mentionnant explicitement les limites de données et les hypothèses de travail.

Un consultant junior fait le même travail en 2 à 3 jours. Un consultant senior intervient en relecture, exactement comme le fait l'agent Partner Review intégré.

## Features

- **9 agents spécialisés** avec rôles distincts (Framer, Hunter, Analyst, Benchmarker, Risk-Scorer, Strategist, Synthesizer, Producer, Partner Review)
- **8 types de mission** préconfigurés (étude de marché, benchmark, DD M&A, entry strategy, business plan, pricing, operations, digital transformation)
- **3 modes de vitesse** (Express 10-20 min, Standard 30-60 min, Exhaustif 60-100 min)
- **Composition d'équipe dynamique**: le Chief invoque les agents selon le template de mission choisi
- **Partner Review intégré**: QA senior qui challenge le livrable et demande des rerolls ciblés avant publication
- **Upload de documents**: PDF, DOCX, XLSX, images, utilisés comme sources primaires par le Hunter
- **Révisions à la demande**: bouton "Demander une révision" post-livraison avec consigne libre
- **Boutons Arrêter et Reprendre**: contrôle complet sur les études en cours
- **Interface SaaS business**: pensée pour utilisateur non-technique (pas de terminal, pas de journal visible par défaut)
- **Mode Pro OAuth ou API**: fonctionne avec un abonnement Claude Pro OU avec une clé API Anthropic (routing CCR optionnel vers Kimi, GPT, Gemini)
- **Livrables téléchargeables**: fichiers .pptx .docx .pdf générés via python-pptx, python-docx, reportlab
- **Workspace filesystem**: chaque engagement est un dossier auto-contenu, git-trackable, auditable

## Quick Start

### Prérequis

- Python 3.11+ ([python.org](https://www.python.org/downloads/))
- Node.js 20+ ([nodejs.org](https://nodejs.org))
- Compte Claude Pro ou clé API Anthropic

### Installation

```bash
git clone https://github.com/JEMALIACHRAF/Atelier.git
cd atelier
pip install -r requirements.txt
npm install -g @anthropic-ai/claude-code
claude login
```

### Lancement

```bash
# Windows
start.bat

# macOS / Linux
python -m uvicorn backend.main:app --host 127.0.0.1 --port 7777
```

Ouvrir [http://localhost:7777](http://localhost:7777) dans le navigateur.

## How it works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Vous · Navigateur · http://localhost:7777                  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│  Frontend · Alpine.js + Tailwind · 3 vues                   │
│  Dashboard · Nouvelle étude · Détail                        │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST + WebSocket
┌──────────────────────────────▼──────────────────────────────┐
│  Backend · FastAPI · Python 3.11                            │
│  Endpoints upload, create, start, stop, revise              │
└──────────────────────────────┬──────────────────────────────┘
                               │ subprocess spawn
┌──────────────────────────────▼──────────────────────────────┐
│  Claude Code CLI · Chief orchestrator                       │
│  Lit mission template, dispatche agents en séquence         │
└──────────────────────────────┬──────────────────────────────┘
                               │ Task tool (synchrone)
┌──────────────────────────────▼──────────────────────────────┐
│  Agents · Markdown prompts dans .claude/agents/*.md         │
│  Framer · Hunter · Analyst · Benchmarker · Risk-Scorer      │
│  Strategist · Synthesizer · Producer · Partner Review       │
└──────────────────────────────┬──────────────────────────────┘
                               │ Read/Write
┌──────────────────────────────▼──────────────────────────────┐
│  Workspace · Filesystem partagé                             │
│  workspace/engagements/{slug}/                              │
│  00_brief.md · 01_workplan.md · 02_data · 03_charts         │
│  04_models · 05_synthesis.md · 06_deliverables · ...        │
└─────────────────────────────────────────────────────────────┘
```

### Workflow d'un engagement

1. **Chief** lit le brief et le template de mission (`templates/missions/{type}.yaml`)
2. **Framer** produit `01_workplan.md`: hypothesis tree MECE, data points P1/P2/P3, analyses prévues
3. **Hunter** collecte via WebSearch/WebFetch (+ documents uploadés), écrit `02_data/sources.json` avec citations
4. **Analyst / Benchmarker / Risk-Scorer / Strategist** (selon mission) produisent charts et modèles dans `03_charts/` et `04_models/`
5. **Synthesizer** extrait insights, rédige `05_synthesis.md` answer-first pyramid principle
6. **Producer** génère `06_deliverables/deck.pptx`, `report.docx`, `exec_summary.pdf` via python-pptx/docx/reportlab
7. **Partner Review** challenge le livrable, demande des rerolls ciblés si nécessaire
8. **Chief** approuve, marque "done", notifie l'UI

Chaque étape écrit sur disque et log ses décisions. Un crash en cours de route n'est pas fatal: le Chief relit l'état filesystem et reprend là où il s'est arrêté.

## Mission templates

| Type | Agents actifs | Durée Standard | Cas d'usage |
|------|---------------|----------------|-------------|
| **Étude de marché** | framer, hunter, analyst, synthesizer, producer, partner_review | ~45 min | Cartographie, sizing, projections |
| **Benchmark concurrentiel** | framer, hunter, benchmarker, synthesizer, producer, partner_review | ~35 min | Positionnement vs concurrents |
| **Due diligence M&A** | framer, hunter, analyst, risk_scorer, synthesizer, producer, partner_review | ~50 min | Red flags, questions management |
| **Stratégie d'entrée** | framer, hunter, analyst, strategist, synthesizer, producer, partner_review | ~45 min | Marché nouveau, segment |
| **Business plan** | framer, hunter, analyst, strategist, synthesizer, producer, partner_review | ~50 min | Trajectoire 3-5 ans |
| **Pricing** | framer, hunter, analyst, strategist, synthesizer, producer, partner_review | ~40 min | Architecture, impact |
| **Diagnostic opérationnel** | framer, hunter, analyst, synthesizer, producer, partner_review | ~45 min | Leviers coût/qualité/délai |
| **Transformation digitale** | framer, hunter, analyst, strategist, synthesizer, producer, partner_review | ~50 min | Maturité + roadmap |

Templates éditables dans `templates/missions/*.yaml`.

## Agents

Chaque agent est défini par un markdown avec frontmatter YAML dans `.claude/agents/`. Modifiable à chaud, sans redémarrage.

| Agent | Modèle | Mission |
|-------|--------|---------|
| **Framer** | Opus | Scoping MECE, hypothesis tree, workplan structuré |
| **Hunter** | Sonnet | Collecte autonome via web APIs et documents uploadés, chaque chiffre sourcé |
| **Analyst** | Sonnet | Market sizing, benchmarks, charts matplotlib, modèles xlsx |
| **Benchmarker** | Sonnet | Matrices concurrentielles 0-3 par dimension, heatmap, radar chart |
| **Risk-Scorer** | Opus | Red flags severité x probabilité, Q&A management |
| **Strategist** | Opus | 3 options stratégiques évaluées, recommandation tranchée |
| **Synthesizer** | Opus | Insights, verdicts hypothèses, narrative pyramid principle |
| **Producer** | Sonnet | Génère .pptx .docx .pdf finaux via python-pptx/docx/reportlab |
| **Partner Review** | Opus | QA senior: thèse, messages, sources, actionabilité, demande rerolls |

## Configuration

### Variables d'environnement (`.env`)

```ini
# Authentification (laisser vide pour mode Pro OAuth)
ANTHROPIC_API_KEY=

# Modèle par défaut: sonnet | opus | haiku
ATELIER_MODEL=sonnet

# Clés web (optionnelles, pour renforcer le Hunter)
TAVILY_API_KEY=
FIRECRAWL_API_KEY=
EXA_API_KEY=
```

### MCP servers

Par défaut: filesystem seul. Pour activer Tavily, Firecrawl, Exa:

```bash
mv .mcp.json.example .mcp.json
# puis renseigner les clés dans .env
```

### Routing multi-provider (CCR)

Si `ANTHROPIC_API_KEY` est renseignée, Atelier démarre automatiquement Claude Code Router en arrière-plan pour router selon `.ccr/config.json`:

```json
{
  "Router": {
    "default": "anthropic,claude-sonnet-5-5",
    "think": "anthropic,claude-opus-4-7",
    "background": "moonshot,kimi-k2",
    "longContext": "google,gemini-2.5-pro"
  }
}
```

## Deliverables

Chaque engagement produit (selon demande):

- **Deck PowerPoint** 10 à 30 slides, titres-messages, chaque chiffre sourcé D#/S#
- **Rapport Word** 10 à 30 pages, méthodologie, bibliographie complète
- **Executive summary PDF** 1 page, 3 à 5 chiffres clés, implications

Génération via:
- [python-pptx](https://github.com/scanny/python-pptx) pour PowerPoint
- [python-docx](https://github.com/python-openxml/python-docx) pour Word
- [reportlab](https://www.reportlab.com/) pour PDF
- [matplotlib](https://matplotlib.org/) pour charts
- [openpyxl](https://openpyxl.readthedocs.io/) pour xlsx annexes

## Workspace structure

```
atelier/
├── CLAUDE.md                     # Mémoire persistante du Chief
├── .claude/
│   ├── settings.json             # Permissions tools
│   └── agents/                   # Prompts des 9 agents (markdown)
├── backend/
│   └── main.py                   # FastAPI (upload, REST, WebSocket, spawn)
├── frontend/
│   ├── index.html                # UI Alpine.js
│   ├── app.js
│   └── style.css
├── templates/
│   └── missions/*.yaml           # 8 templates de mission
├── workspace/
│   ├── backlog/                  # Études en attente de lancement
│   ├── engagements/              # Études en cours ou terminées
│   │   └── {slug}/
│   │       ├── _attachments/     # Documents uploadés
│   │       ├── _meta.json        # Mission type, speed mode
│   │       ├── 00_brief.md
│   │       ├── 01_workplan.md
│   │       ├── 02_data/sources.json
│   │       ├── 03_charts/*.png
│   │       ├── 04_models/*.py
│   │       ├── 05_synthesis.md
│   │       ├── 06_deliverables/  # Livrables téléchargeables
│   │       └── 07_partner_review.md
│   └── templates/
│       └── brand_palette.json    # Palette couleurs par défaut
├── .ccr/config.json              # Router modèles (mode API)
├── .mcp.json                     # Serveurs MCP activés
├── requirements.txt              # Deps Python
└── start.bat                     # Lanceur Windows
```



## Technical stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) 0.110+
- [Uvicorn](https://www.uvicorn.org/) ASGI server
- [Pydantic](https://docs.pydantic.dev/) data validation
- [PyYAML](https://pyyaml.org/) templates
- [python-multipart](https://andrew-d.github.io/python-multipart/) uploads

**Frontend**
- [Alpine.js](https://alpinejs.dev/) 3.13 reactive UI (zero build)
- Instrument Serif + Inter (Google Fonts)

**Agent runtime**
- [Claude Code](https://docs.claude.com/en/docs/claude-code) CLI
- [Claude Code Router](https://github.com/musistudio/claude-code-router) (optionnel)

**Document generation**
- [python-pptx](https://github.com/scanny/python-pptx)
- [python-docx](https://github.com/python-openxml/python-docx)
- [reportlab](https://www.reportlab.com/)
- [matplotlib](https://matplotlib.org/)
- [openpyxl](https://openpyxl.readthedocs.io/)



## License

MIT License. Voir [`LICENSE`](./LICENSE).

---
<div align="center">

**Built by [Achraf Jemali](https://github.com/JEMALIACHRAF)** · Data & AI Engineer 

[Report a bug](https://github.com/JEMALIACHRAF/cloud-agent-v2/issues) · [Request a feature](https://github.com/JEMALIACHRAF/cloud-agent-v2/issues) · [Discussions](https://github.com/JEMALIACHRAF/cloud-agent-v2/discussions)

</div>
