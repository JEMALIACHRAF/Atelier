function atelier() {
  return {
    view: 'dashboard',
    activeTab: 'brief',
    engagements: [],
    backlog: [],
    missions: [],
    selectedMission: null,
    detail: { slug: null, title: '', stage: 'pending', deliverables: [], attachments: [], form_data: {}, log: '' },
    logLines: [],
    ws: null,
    health: { ok: false, mode: 'pro' },
    form: { title: '', brief: '', deliverables: ['deck', 'report'], mission_type: 'market_study', speed_mode: 'standard', form_data: {} },
    submitting: false,
    formError: null,
    pollTimer: null,
    pendingFiles: [],
    dragging: false,
    showRevision: false,
    revisionText: '',
    revisionSubmitting: false,
    stopping: false,

    workflowSteps: [
      { key: 'framing', label: 'Cadrage' },
      { key: 'hunting', label: 'Collecte' },
      { key: 'analyzing', label: 'Analyse' },
      { key: 'synthesizing', label: 'Synthèse' },
      { key: 'producing', label: 'Livrables' },
      { key: 'done', label: 'Terminée' },
    ],

    get nbDone() {
      return this.engagements.filter(e => e.stage === 'done').length;
    },
    get activeList() {
      return this.engagements.filter(e => e.stage !== 'done' && e.stage !== 'backlog');
    },
    get doneList() {
      return this.engagements.filter(e => e.stage === 'done');
    },

    async init() {
      await this.checkHealth();
      await this.loadMissions();
      await this.refresh();
      if (location.hash.startsWith('#e/')) {
        this.openDetail(location.hash.slice(3));
      }
      this.pollTimer = setInterval(() => {
        if (this.view === 'dashboard') this.refresh();
        if (this.view === 'detail' && this.detail.slug) this.loadDetail(this.detail.slug, false);
      }, 5000);
    },

    async checkHealth() {
      try {
        const r = await fetch('/api/health');
        const data = await r.json();
        this.health = { ok: !!data.claude_cli_installed, mode: data.mode || 'pro' };
      } catch (e) {
        this.health = { ok: false, mode: 'pro' };
      }
    },

    async loadMissions() {
      try {
        const r = await fetch('/api/missions');
        const data = await r.json();
        this.missions = data.missions || [];
        // ensure fallback in case the server returned nothing
        if (this.missions.length === 0) {
          this.missions = [{ id: 'market_study', name: 'Étude de marché', short: 'Cartographier un marché.', icon: 'chart', color: 'navy', agents: ['framer','hunter','analyst','synthesizer','producer'], estimated_duration_min: 45 }];
        }
      } catch (e) {
        console.error('loadMissions failed', e);
      }
    },

    missionNameFromType(type) {
      const m = this.missions.find(x => x.id === type);
      return m ? m.name : 'Étude';
    },

    goTo(view) {
      if (view !== 'detail') {
        this.closeWs();
        location.hash = '';
      }
      this.view = view;
      if (view === 'dashboard') this.refresh();
    },

    selectMission(mission) {
      this.selectedMission = mission;
      this.form.mission_type = mission.id;
      this.form.deliverables = [...(mission.default_deliverables || ['deck', 'report'])];
      this.form.speed_mode = 'standard';
      this.form.form_data = {};
      this.form.title = '';
      this.form.brief = '';
      this.pendingFiles = [];
      this.formError = null;
      this.view = 'new-brief';
    },

    speedDurationLabel(mode) {
      if (!this.selectedMission || !this.selectedMission.speed_modes) {
        return mode === 'express' ? '~15 min' : mode === 'deep' ? '~90 min' : '~45 min';
      }
      const sm = this.selectedMission.speed_modes[mode];
      if (sm && sm.duration_min) return `~${sm.duration_min} min`;
      return mode;
    },

    async stopEngagement(slug) {
      if (!confirm('Arrêter l\'étude en cours ? Les livrables déjà produits restent disponibles, et vous pourrez relancer plus tard pour reprendre.')) return;
      this.stopping = true;
      try {
        const r = await fetch(`/api/engagements/${encodeURIComponent(slug)}/stop`, { method: 'POST' });
        if (!r.ok) {
          const err = await r.json().catch(() => ({ detail: r.statusText }));
          alert('Impossible d\'arrêter: ' + (err.detail || r.statusText));
          return;
        }
        await this.loadDetail(slug, false);
        await this.refresh();
      } catch (e) {
        alert('Erreur: ' + e.message);
      } finally {
        this.stopping = false;
      }
    },

    async submitRevision() {
      if (!this.detail.slug || this.revisionText.length < 5) return;
      this.revisionSubmitting = true;
      try {
        const r = await fetch(`/api/engagements/${encodeURIComponent(this.detail.slug)}/revise`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ instructions: this.revisionText }),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({ detail: r.statusText }));
          alert('Impossible de lancer la révision: ' + (err.detail || r.statusText));
          return;
        }
        this.revisionText = '';
        this.showRevision = false;
        await this.loadDetail(this.detail.slug, true);
      } catch (e) {
        alert('Erreur: ' + e.message);
      } finally {
        this.revisionSubmitting = false;
      }
    },

    async refresh() {
      try {
        const r = await fetch('/api/engagements');
        const data = await r.json();
        this.engagements = data.engagements || [];
        this.backlog = data.backlog || [];
      } catch (e) {
        console.error('refresh failed', e);
      }
    },

    // -- file handling --
    handleFiles(fileList) {
      for (const f of fileList) {
        this.pendingFiles.push(f);
      }
    },
    handleDrop(ev) {
      this.dragging = false;
      if (ev.dataTransfer && ev.dataTransfer.files) {
        this.handleFiles(ev.dataTransfer.files);
      }
    },
    removeFile(idx) {
      this.pendingFiles.splice(idx, 1);
    },

    async createEngagement() {
      this.submitting = true;
      this.formError = null;
      try {
        const r = await fetch('/api/engagements', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.form),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({ detail: r.statusText }));
          throw new Error(err.detail || 'Erreur serveur');
        }
        const data = await r.json();

        // Upload attachments if any
        if (this.pendingFiles.length > 0) {
          await this.uploadToExisting(data.slug, this.pendingFiles);
        }

        // Reset form state
        const slug = data.slug;
        this.form = { title: '', brief: '', deliverables: ['deck', 'report'], mission_type: 'market_study', speed_mode: 'standard', form_data: {} };
        this.pendingFiles = [];

        await this.refresh();
        // Auto-start the engagement after creation
        await this.startEngagement(slug);
      } catch (e) {
        this.formError = e.message || String(e);
      } finally {
        this.submitting = false;
      }
    },

    async uploadToExisting(slug, files) {
      if (!files || files.length === 0) return;
      const fd = new FormData();
      for (const f of files) fd.append('files', f);
      try {
        const r = await fetch(`/api/engagements/${encodeURIComponent(slug)}/attachments`, {
          method: 'POST',
          body: fd,
        });
        const data = await r.json().catch(() => ({}));
        if (data.rejected && data.rejected.length > 0) {
          alert('Certains fichiers n\'ont pas pu être ajoutés:\n' + data.rejected.map(r => r.name + ': ' + r.reason).join('\n'));
        }
        if (this.detail.slug === slug) {
          await this.loadDetail(slug, false);
        }
      } catch (e) {
        console.error('upload failed', e);
        alert('Erreur lors du téléversement');
      }
    },

    async deleteAttachment(slug, name) {
      if (!confirm('Retirer ' + name + ' de l\'étude ?')) return;
      try {
        await fetch(`/api/engagements/${encodeURIComponent(slug)}/attachments/${encodeURIComponent(name)}`, { method: 'DELETE' });
        await this.loadDetail(slug, false);
      } catch (e) {
        console.error('delete failed', e);
      }
    },

    async startEngagement(slug) {
      try {
        const r = await fetch(`/api/engagements/${encodeURIComponent(slug)}/start`, { method: 'POST' });
        if (!r.ok) {
          const err = await r.json().catch(() => ({ detail: r.statusText }));
          alert('Impossible de lancer: ' + (err.detail || r.statusText));
          return;
        }
        await this.refresh();
        this.openDetail(slug);
      } catch (e) {
        alert('Erreur: ' + e.message);
      }
    },

    async openDetail(slug) {
      this.view = 'detail';
      this.activeTab = 'brief';
      location.hash = 'e/' + slug;
      await this.loadDetail(slug, true);
      // Auto-switch to livrables tab if the study is already done
      if (this.detail.stage === 'done' && (this.detail.deliverables || []).length > 0) {
        this.activeTab = 'livrables';
      }
      this.connectWs(slug);
    },

    async loadDetail(slug, resetLog) {
      try {
        const r = await fetch(`/api/engagements/${encodeURIComponent(slug)}`);
        if (!r.ok) {
          this.detail = { slug, title: 'Étude introuvable', stage: 'error', deliverables: [], attachments: [], form_data: {} };
          return;
        }
        const data = await r.json();
        this.detail = data;
        if (resetLog) {
          this.logLines = [];
          if (data.log) {
            const lines = data.log.split('\n').filter(Boolean).slice(-100);
            lines.forEach((line) => {
              const m = line.match(/^\[([\d:]+)\]\s+(\w+):\s+(.*)$/);
              if (m) this.logLines.push({ ts: m[1], type: m[2], msg: m[3] });
              else this.logLines.push({ ts: '', type: 'info', msg: line });
            });
          }
        }
      } catch (e) {
        console.error('loadDetail failed', e);
      }
    },

    connectWs(slug) {
      this.closeWs();
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const url = `${proto}://${location.host}/ws/engagements/${encodeURIComponent(slug)}`;
      try {
        this.ws = new WebSocket(url);
        this.ws.onmessage = (ev) => {
          try {
            const event = JSON.parse(ev.data);
            if (event.type === 'connected') return;
            if (event.type === 'chief_log') {
              const m = event.msg.match(/^\[([\d:]+)\]\s+(\w+):\s+(.*)$/);
              if (m) {
                const sig = m[1] + '|' + m[3];
                if (this._recentEmits && this._recentEmits.has(sig)) return;
                this.logLines.push({ ts: m[1], type: m[2], msg: m[3] });
              } else {
                this.logLines.push({ ts: event.ts, type: 'chief_log', msg: event.msg });
              }
            } else {
              this.logLines.push(event);
              this._recentEmits = this._recentEmits || new Set();
              const sig = event.ts + '|' + event.msg;
              this._recentEmits.add(sig);
              setTimeout(() => { this._recentEmits && this._recentEmits.delete(sig); }, 3000);
            }
            if (this.logLines.length > 400) this.logLines = this.logLines.slice(-400);
            if (event.type === 'done' || event.type === 'error' || event.type === 'warn') {
              this.loadDetail(slug, false);
            }
          } catch (e) {
            console.error('ws parse', e);
          }
        };
      } catch (e) {
        console.error('ws connect failed', e);
      }
    },

    closeWs() {
      if (this.ws) {
        try { this.ws.close(); } catch (e) { /* ignore */ }
        this.ws = null;
      }
    },

    stageProgress(stage) {
      const order = ['pending', 'backlog', 'framing', 'hunting', 'analyzing', 'synthesizing', 'producing', 'done'];
      const i = order.indexOf(stage);
      if (i <= 0) return 0;
      return Math.round((i / (order.length - 1)) * 100);
    },

    stageLabel(stage) {
      const map = {
        pending: 'En attente',
        backlog: 'À lancer',
        framing: 'Cadrage et plan de travail',
        hunting: 'Collecte des données',
        analyzing: 'Analyse quantitative',
        synthesizing: 'Rédaction de la synthèse',
        producing: 'Production des livrables',
        done: 'Terminée',
        error: 'Erreur, à relancer',
      };
      return map[stage] || stage;
    },

    stepClass(stepKey) {
      const order = ['framing', 'hunting', 'analyzing', 'synthesizing', 'producing', 'done'];
      const current = order.indexOf(this.detail.stage);
      const target = order.indexOf(stepKey);
      if (current < 0 || target < 0) return '';
      if (target < current) return 'done';
      if (target === current) return 'active';
      return '';
    },

    deliverableIcon(name) {
      if (name.endsWith('.pptx') || name.endsWith('.ppt')) return 'P';
      if (name.endsWith('.docx') || name.endsWith('.doc')) return 'W';
      if (name.endsWith('.pdf')) return 'PDF';
      if (name.endsWith('.xlsx') || name.endsWith('.xls')) return 'X';
      return '▤';
    },

    formatSize(bytes) {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },
  };
}
