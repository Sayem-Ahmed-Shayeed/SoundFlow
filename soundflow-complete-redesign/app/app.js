(() => {
  'use strict';

  const app = document.querySelector('#app');
  const toastRegion = document.querySelector('#toastRegion');
  const modalRoot = document.querySelector('#modalRoot');

  const state = {
    recording: false,
    recordSeconds: 0,
    recordTimer: null,
    historyFilter: 'all',
    historySearch: '',
    playgroundTemplate: 'rewrite',
    playgroundResult: '',
    aiEnabled: true,
    apiVisible: false,
    autoPolish: true,
    model: 'small',
    downloads: {},
    shortcutCapture: false,
    shortcut: ['Ctrl', 'Alt', 'Space'],
    systemStatus: 'idle',
    settings: {
      theme: 'dark',
      timeout: 380,
      copyPhrases: true,
      startup: true,
      autoInsert: true,
      floatingWidget: true,
      autoSave: true,
      terminalPaste: true,
      listenBackground: true,
      language: 'Auto detect',
      provider: 'Gemini (fast)',
      modelName: 'gemini-3.5-flash',
      style: 'Concise rewrite'
    },
    transcripts: [
      {
        id: 1,
        group: 'Today',
        time: '7:23 PM',
        duration: '00:05',
        words: 10,
        text: 'I am checking if the transcription and polishing are working.'
      },
      {
        id: 2,
        group: 'Today',
        time: '7:21 PM',
        duration: '00:05',
        words: 23,
        text: 'Yes, it is working! I am online, responsive, and ready to help you test.\n\nHow can I assist you with your trial today?'
      }
    ]
  };

  const icons = (name, cls = '') => `<svg class="${cls}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
  const escapeHTML = (str) => String(str).replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const route = () => (location.hash || '#/dictation').replace(/^#\//, '').split('/');

  function toast(message, icon = 'check') {
    const el = document.createElement('div');
    el.className = 'toast';
    el.innerHTML = `${icons(icon)}<span>${escapeHTML(message)}</span>`;
    toastRegion.appendChild(el);
    window.setTimeout(() => el.remove(), 2800);
  }

  function modal({ title, body, confirm = 'Confirm', destructive = false, onConfirm }) {
    modalRoot.innerHTML = `
      <div class="modal-backdrop" role="presentation" data-modal-close>
        <section class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" onclick="event.stopPropagation()">
          <h2 id="modal-title">${escapeHTML(title)}</h2>
          <p>${escapeHTML(body)}</p>
          <div class="modal-actions">
            <button class="button" type="button" data-modal-close>Cancel</button>
            <button class="button ${destructive ? 'button--danger' : 'button--primary'}" type="button" data-modal-confirm>${escapeHTML(confirm)}</button>
          </div>
        </section>
      </div>`;
    const close = () => { modalRoot.innerHTML = ''; };
    modalRoot.querySelectorAll('[data-modal-close]').forEach(el => el.addEventListener('click', close));
    modalRoot.querySelector('[data-modal-confirm]').addEventListener('click', () => { onConfirm?.(); close(); });
    modalRoot.querySelector('[data-modal-confirm]').focus();
  }

  function updateNavigation() {
    const [root] = route();
    document.querySelectorAll('[data-route]').forEach(link => {
      const active = link.dataset.route === (root === 'preferences' ? 'preferences' : root);
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
  }

  function pageHeader({ eyebrow, title, subtitle, actions = '' }) {
    return `
      <header class="page-header">
        <div>
          ${eyebrow ? `<div class="eyebrow">${escapeHTML(eyebrow)}</div>` : ''}
          <h1 class="page-title">${escapeHTML(title)}</h1>
          ${subtitle ? `<p class="page-subtitle">${escapeHTML(subtitle)}</p>` : ''}
        </div>
        ${actions ? `<div class="page-actions">${actions}</div>` : ''}
      </header>`;
  }

  function waveformBars() {
    return Array.from({length: 31}, (_, i) => `<span style="animation-duration:${620 + (i%7)*48}ms"></span>`).join('');
  }

  function renderDictation() {
    const status = state.recording
      ? `<span class="status-chip status-chip--live"><span class="status-dot status-dot--live"></span>Listening</span>`
      : `<span class="status-chip status-chip--ready"><span class="status-dot status-dot--ready"></span>Ready</span>`;

    const title = state.recording ? `Listening · ${formatTimer(state.recordSeconds)}` : 'Ready to dictate';
    const instruction = state.recording ? 'Release to transcribe · Esc to cancel' : 'Hold the shortcut, speak naturally, then release to insert.';

    app.innerHTML = `
      <section class="page" aria-labelledby="page-title">
        ${pageHeader({
          eyebrow: 'Private voice input',
          title: 'Dictation',
          subtitle: 'Fast, private speech-to-text that works wherever you type.',
          actions: `${status}<select class="select" id="languageSelect" aria-label="Dictation language" style="width:160px"><option>Auto detect</option><option>English</option><option>Spanish</option><option>French</option><option>German</option></select>`
        })}

        <section class="dictation-stage" aria-label="Dictation control">
          <div class="dictation-stage-inner">
            <div class="dictation-kicker">${state.recording ? 'Microphone active' : 'On-device microphone ready'}</div>
            <h2 class="dictation-title">${title}</h2>
            <p class="dictation-instruction">${instruction}</p>

            <div class="mic-area">
              <div class="waveform ${state.recording ? 'live' : ''}" aria-hidden="true">${waveformBars()}</div>
              <button class="mic-button ${state.recording ? 'recording' : ''}" id="micButton" type="button" aria-pressed="${state.recording}" aria-label="${state.recording ? 'Stop recording' : 'Start recording'}">
                ${icons(state.recording ? 'stop' : 'mic')}
              </button>
            </div>

            <div class="shortcut-line"><span>${state.recording ? 'Or press' : 'Push-to-talk'}</span><kbd>Ctrl</kbd><span>+</span><kbd>Alt</kbd><span>+</span><kbd>Space</kbd></div>
          </div>
        </section>

        <section class="session-rail" aria-label="Session summary">
          <div class="session-item">
            <div class="session-label">Today</div>
            <div class="session-value">33 words</div>
            <div class="session-meta">2 dictations</div>
          </div>
          <div class="session-item">
            <div class="session-label">Last dictation</div>
            <div class="session-text">I am checking if the transcription and polishing are working.</div>
            <div class="session-meta">7:23 PM · 10 words</div>
          </div>
          <div class="session-item">
            <div class="session-label">Engine</div>
            <div class="session-value">Small · CUDA</div>
            <div class="session-meta">Local Whisper · INT8</div>
          </div>
        </section>
      </section>`;

    document.querySelector('#micButton').addEventListener('click', toggleRecording);
    document.querySelector('#languageSelect').value = state.settings.language;
    document.querySelector('#languageSelect').addEventListener('change', e => state.settings.language = e.target.value);
  }

  function formatTimer(seconds) {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  function toggleRecording() {
    if (!state.recording) {
      state.recording = true;
      state.recordSeconds = 0;
      render();
      state.recordTimer = window.setInterval(() => {
        state.recordSeconds++;
        const heading = document.querySelector('.dictation-title');
        if (heading) heading.textContent = `Listening · ${formatTimer(state.recordSeconds)}`;
      }, 1000);
    } else {
      state.recording = false;
      window.clearInterval(state.recordTimer);
      state.recordTimer = null;
      render();
      toast('Inserted 18 words at the cursor.');
    }
  }

  function renderHistory() {
    const query = state.historySearch.trim().toLowerCase();
    const filtered = state.transcripts.filter(t => {
      const matchesSearch = !query || t.text.toLowerCase().includes(query);
      const matchesFilter = state.historyFilter === 'all' || (state.historyFilter === 'today' && t.group === 'Today');
      return matchesSearch && matchesFilter;
    });

    app.innerHTML = `
      <section class="page" aria-labelledby="page-title">
        ${pageHeader({ title: 'History', subtitle: 'Search, edit, copy, and reuse transcripts saved locally.' })}
        <div class="toolbar">
          <label class="search-field">
            ${icons('search')}
            <span class="sr-only"></span>
            <input class="input" id="historySearch" type="search" value="${escapeHTML(state.historySearch)}" placeholder="Search transcripts" aria-label="Search transcripts" />
          </label>
          <select class="select filter-select" id="historyFilter" aria-label="Filter history">
            <option value="all">All transcripts</option>
            <option value="today">Today</option>
          </select>
        </div>
        <div class="group-label">Today · ${filtered.length}</div>
        ${filtered.length ? `<div class="transcript-list">${filtered.map(transcriptRow).join('')}</div>` : `<div class="empty-state"><strong>No matching transcripts</strong>Try a broader search or clear the filter.</div>`}
      </section>`;

    const search = document.querySelector('#historySearch');
    search.addEventListener('input', e => {
      state.historySearch = e.target.value;
      window.clearTimeout(search._timer);
      search._timer = window.setTimeout(renderHistory, 120);
    });
    search.focus({preventScroll:true});
    try { search.setSelectionRange(search.value.length, search.value.length); } catch {}

    const filter = document.querySelector('#historyFilter');
    filter.value = state.historyFilter;
    filter.addEventListener('change', e => { state.historyFilter = e.target.value; renderHistory(); });

    bindHistoryActions();
  }

  function transcriptRow(t) {
    return `
      <article class="transcript-row" data-transcript="${t.id}">
        <div class="transcript-meta"><strong>${escapeHTML(t.time)}</strong><span>${escapeHTML(t.duration)} · ${t.words} words</span></div>
        <div class="transcript-body"><p class="transcript-text">${escapeHTML(t.text)}</p></div>
        <div class="row-actions" aria-label="Transcript actions">
          <button class="button button--quiet icon-button" type="button" data-action="edit" title="Edit transcript" aria-label="Edit transcript">${icons('edit')}</button>
          <button class="button button--quiet icon-button" type="button" data-action="copy" title="Copy transcript" aria-label="Copy transcript">${icons('copy')}</button>
          <button class="button button--quiet icon-button" type="button" data-action="polish" title="Polish transcript" aria-label="Polish transcript">${icons('spark')}</button>
          <button class="button button--quiet icon-button" type="button" data-action="more" title="More options" aria-label="More options">${icons('more')}</button>
        </div>
      </article>`;
  }

  function bindHistoryActions() {
    document.querySelectorAll('.transcript-row').forEach(row => {
      const id = Number(row.dataset.transcript);
      row.querySelectorAll('[data-action]').forEach(btn => btn.addEventListener('click', () => historyAction(id, btn.dataset.action, row)));
    });
  }

  function historyAction(id, action, row) {
    const t = state.transcripts.find(x => x.id === id);
    if (!t) return;
    if (action === 'copy') {
      navigator.clipboard?.writeText(t.text).catch(() => {});
      toast('Transcript copied.');
    } else if (action === 'polish') {
      t.text = t.text.replace('I am checking if', 'I’m checking whether').replace('Yes, it is working!', 'Yes — it’s working.');
      t.words = t.text.split(/\s+/).filter(Boolean).length;
      renderHistory();
      toast('Transcript polished.');
    } else if (action === 'edit') {
      const p = row.querySelector('.transcript-text');
      if (p.contentEditable === 'true') {
        t.text = p.innerText.trim();
        t.words = t.text.split(/\s+/).filter(Boolean).length;
        p.contentEditable = 'false';
        toast('Transcript saved.');
      } else {
        p.contentEditable = 'true';
        p.focus();
        btnIconSwap(row, 'edit', 'check');
      }
    } else if (action === 'more') {
      modal({
        title: 'Delete transcript?',
        body: 'This transcript is stored locally. Deleting it cannot be undone.',
        confirm: 'Delete',
        destructive: true,
        onConfirm: () => {
          state.transcripts = state.transcripts.filter(x => x.id !== id);
          renderHistory();
          toast('Transcript deleted.');
        }
      });
    }
  }

  function btnIconSwap(row, action, newIcon) {
    const btn = row.querySelector(`[data-action="${action}"]`);
    if (btn) btn.innerHTML = icons(newIcon);
  }

  function renderPlayground() {
    const templates = {
      insert: { title: 'Insert text', hint: 'Put clean text at the cursor.', placeholder: 'Type the text you want to insert…' },
      format: { title: 'Format text', hint: 'Transform selected text into a clearer structure.', placeholder: 'Paste text to format…' },
      rewrite: { title: 'Smart rewrite', hint: 'Improve clarity while preserving meaning.', placeholder: 'Paste or dictate text to rewrite…' }
    };
    const current = templates[state.playgroundTemplate];
    app.innerHTML = `
      <section class="page" aria-labelledby="page-title">
        ${pageHeader({ title:'Playground', subtitle:'Practice Soundflow commands before using them in other applications.' })}
        <div class="playground-grid">
          <section class="command-panel" aria-labelledby="command-title">
            <h2 class="section-title" id="command-title">Try a command</h2>
            <p class="section-copy">Choose a template or write your own instruction.</p>
            <div class="template-grid">
              ${Object.entries(templates).map(([key, value]) => `<button class="template ${state.playgroundTemplate===key?'active':''}" data-template="${key}" type="button"><strong>${value.title}</strong><span>${value.hint}</span></button>`).join('')}
            </div>
            <label class="label" for="playgroundInput">Input</label>
            <textarea class="textarea" id="playgroundInput" placeholder="${escapeHTML(current.placeholder)}"></textarea>
            <div class="command-actions">
              <span class="command-hint">Runs locally unless AI Polish is explicitly used.</span>
              <button class="button button--primary" id="runCommand" type="button">Run command ${icons('arrow')}</button>
            </div>

            <div class="example-list" aria-label="Examples">
              <button class="example-button" type="button" data-example="Turn this into concise bullet points with clear action items."><span>Meeting notes → action items</span><span>Format</span></button>
              <button class="example-button" type="button" data-example="Rewrite this to sound warm, direct, and concise while preserving every key fact."><span>Polish a message</span><span>Rewrite</span></button>
              <button class="example-button" type="button" data-example="Insert: Thanks — I’ll review this and get back to you tomorrow."><span>Reusable response</span><span>Insert</span></button>
            </div>
          </section>

          <section class="preview-panel" aria-labelledby="preview-title">
            <h2 class="section-title" id="preview-title">Preview</h2>
            <p class="section-copy">See the result before using it elsewhere.</p>
            <div class="preview-surface" id="previewSurface">
              ${state.playgroundResult ? `<div class="preview-meta"><span>Result</span><span>Local preview</span></div><div class="preview-result">${escapeHTML(state.playgroundResult)}</div>` : `<div class="preview-placeholder"><div>${icons('spark')}<div style="margin-top:8px">Your result will appear here.</div></div></div>`}
            </div>
          </section>
        </div>
      </section>`;

    document.querySelectorAll('[data-template]').forEach(btn => btn.addEventListener('click', () => { state.playgroundTemplate = btn.dataset.template; renderPlayground(); }));
    document.querySelectorAll('[data-example]').forEach(btn => btn.addEventListener('click', () => {
      const ta = document.querySelector('#playgroundInput');
      ta.value = btn.dataset.example;
      ta.focus();
    }));
    document.querySelector('#runCommand').addEventListener('click', runPlayground);
  }

  function runPlayground() {
    const input = document.querySelector('#playgroundInput').value.trim();
    if (!input) { toast('Add some text or an instruction first.', 'info'); return; }
    if (state.playgroundTemplate === 'insert') {
      state.playgroundResult = input.replace(/^insert:\s*/i, '');
    } else if (state.playgroundTemplate === 'format') {
      const words = input.split(/\s+/).filter(Boolean);
      state.playgroundResult = `• ${words.slice(0, Math.ceil(words.length/3)).join(' ')}\n• ${words.slice(Math.ceil(words.length/3), Math.ceil(words.length*2/3)).join(' ')}\n• ${words.slice(Math.ceil(words.length*2/3)).join(' ')}`;
    } else {
      state.playgroundResult = input.replace(/\bi am\b/gi, 'I’m').replace(/\bit is\b/gi, 'it’s').replace(/\s+/g, ' ').trim();
      state.playgroundResult = state.playgroundResult.charAt(0).toUpperCase() + state.playgroundResult.slice(1);
    }
    renderPlayground();
    toast('Preview updated.');
  }

  const prefItems = [
    ['general','General'],
    ['dictation','Dictation'],
    ['playback','Playback'],
    ['shortcuts','Shortcuts'],
    ['ai-polish','AI Polish'],
    ['system','System']
  ];

  function prefsNav(active) {
    return `<nav class="prefs-nav" aria-label="Preference sections">${prefItems.map(([id,label]) => `<a href="#/preferences/${id}" class="${active===id?'active':''}" ${active===id?'aria-current="page"':''}>${label}</a>`).join('')}</nav>`;
  }

  function renderPreferences(section='general') {
    const valid = prefItems.some(([id]) => id === section) ? section : 'general';
    app.innerHTML = `
      <section class="page" aria-labelledby="page-title">
        ${pageHeader({ title:'Preferences', subtitle:'Tune recognition, behavior, shortcuts, privacy, and system readiness.' })}
        <div class="preferences-shell">
          ${prefsNav(valid)}
          <div class="settings-pane">${renderPreferenceSection(valid)}</div>
        </div>
      </section>`;
    bindPreferenceControls(valid);
  }

  function renderPreferenceSection(section) {
    if (section === 'general') return `
      <section class="settings-section">
        <div class="settings-heading"><h2>Appearance</h2><p>Keep Soundflow comfortable for long sessions.</p></div>
        <div class="setting-list">
          ${settingRow('Theme','Choose the interface appearance.', `<div class="segmented" role="group" aria-label="Theme"><button class="${state.settings.theme==='light'?'active':''}" data-theme="light">Light</button><button class="${state.settings.theme==='dark'?'active':''}" data-theme="dark">Dark</button></div>`)}
        </div>
      </section>
      <section class="settings-section">
        <div class="settings-heading"><h2>Dictation behavior</h2><p>Control when speech is finalized and what happens next.</p></div>
        <div class="setting-list">
          ${settingRow('Silence timeout',`Finalize after about ${state.settings.timeout} ms of silence.`, `<div class="range-wrap"><input id="timeoutRange" type="range" min="250" max="1400" step="10" value="${state.settings.timeout}" aria-label="Silence timeout"><div class="range-labels"><span>Fast</span><span>Patient</span></div></div>`)}
          ${settingRow('Copy completed phrases automatically','Keep the final phrase available on your clipboard.', switchHTML('copyPhrases',state.settings.copyPhrases))}
          ${settingRow('Start in the system tray','Launch Soundflow quietly in the background.', switchHTML('startup',state.settings.startup))}
        </div>
      </section>`;

    if (section === 'dictation') return `
      <section class="settings-section">
        <div class="settings-heading"><h2>Recognition model</h2><p>All models run locally. Larger models trade speed and memory for accuracy.</p></div>
        <div class="model-list">
          ${modelRow('tiny','Fastest · approximately 78 MB')}
          ${modelRow('base','Fast and lightweight · approximately 148 MB')}
          ${modelRow('small','Recommended balance · approximately 486 MB', true)}
          ${modelRow('medium','Higher accuracy · approximately 1.53 GB')}
          ${modelRow('large-v3-turbo','Best quality · approximately 1.62 GB')}
        </div>
      </section>
      <section class="settings-section">
        <div class="settings-heading"><h2>Recognition preferences</h2><p>Choose where models live and how language is detected.</p></div>
        <div class="setting-list">
          ${settingRow('Model directory','Local folder used by the recognition engine.', `<input class="input path-field" value="/home/sha-weed/.local/share/soundflow/models" aria-label="Model directory">`)}
          ${settingRow('Language','Auto detect works well for mixed or changing input.', `<select class="select" id="prefLanguage"><option>Auto detect</option><option>English</option><option>Spanish</option><option>French</option><option>German</option></select>`)}
        </div>
      </section>`;

    if (section === 'playback') return `
      <section class="settings-section">
        <div class="settings-heading"><h2>Playback & insertion</h2><p>Choose how completed speech moves into the application you are using.</p></div>
        <div class="setting-list">
          ${settingRow('Insert text automatically at the cursor','Paste completed dictation into the focused application.',switchHTML('autoInsert',state.settings.autoInsert))}
          ${settingRow('Show floating dictation widget','Display recording and transcription status above other apps.',switchHTML('floatingWidget',state.settings.floatingWidget))}
          ${settingRow('Auto-save transcripts to History','Keep completed dictations locally so they can be reviewed.',switchHTML('autoSave',state.settings.autoSave))}
          ${settingRow('Terminal paste mode','Use terminal-friendly paste behavior for shells and CLI prompts.',switchHTML('terminalPaste',state.settings.terminalPaste))}
        </div>
      </section>`;

    if (section === 'shortcuts') return `
      <section class="settings-section">
        <div class="settings-heading"><h2>Push-to-talk</h2><p>Hold this shortcut to record from anywhere. Release it to transcribe and insert.</p></div>
        <div class="setting-list">
          ${settingRow('Hold to dictate','Click the shortcut, then press a new key combination.', `<div class="shortcut-editor"><button id="shortcutCapture" type="button" class="shortcut-capture ${state.shortcutCapture?'listening':''}">${state.shortcutCapture ? 'Press shortcut…' : state.shortcut.map(k=>`<kbd>${escapeHTML(k)}</kbd>`).join('<span>+</span>')}</button><button class="button button--quiet" id="resetShortcut" type="button">Reset</button></div>`)}
          ${settingRow('Listen while Soundflow is in the background','Enables push-to-talk even when another application is focused.',switchHTML('listenBackground',state.settings.listenBackground))}
        </div>
      </section>
      <div class="notice" style="margin-top:20px">${icons('keyboard')}<div><strong>System shortcut permission</strong>Some Linux desktop environments ask once before a global shortcut can be used.</div></div>`;

    if (section === 'ai-polish') return `
      <section class="settings-section">
        <div class="settings-heading"><h2>AI Polish</h2><p>Optional cleanup for grammar, punctuation, filler words, and style.</p></div>
        <div class="notice ${state.aiEnabled ? 'notice--warning' : 'notice--privacy'}" style="margin-bottom:18px">${icons(state.aiEnabled?'alert':'shield')}<div><strong>${state.aiEnabled ? 'Cloud boundary enabled' : 'On-device only'}</strong>${state.aiEnabled ? 'Transcript text can be sent to the selected AI provider. Audio never leaves this device.' : 'Recognition and transcript storage stay local. No transcript text is sent to an AI provider.'}</div></div>
        <div class="setting-list">
          ${settingRow('Enable AI Polish','Allow transcript text to be sent to the configured provider for cleanup.',switchHTML('aiEnabled',state.aiEnabled))}
          ${settingRow('Polish automatically after dictation','Clean each transcript before it is saved and inserted.',switchHTML('autoPolish',state.autoPolish), !state.aiEnabled)}
        </div>
      </section>
      ${state.aiEnabled ? `<section class="settings-section">
        <div class="settings-heading"><h2>Provider</h2><p>Credentials remain on this device.</p></div>
        <div class="setting-list">
          ${settingRow('Provider','Service used for text cleanup.', `<select class="select" id="providerSelect"><option>Gemini (fast)</option><option>OpenAI</option><option>Custom endpoint</option></select>`)}
          ${settingRow('API key','Stored locally and never included in transcript history.', `<div class="secret-field"><input class="input" id="apiKey" type="${state.apiVisible?'text':'password'}" value="sk-local-demo-key-••••••••••" aria-label="API key"><button class="button icon-button" id="toggleApi" type="button" aria-label="${state.apiVisible?'Hide':'Show'} API key">${icons(state.apiVisible?'eye-off':'eye')}</button></div>`)}
          ${settingRow('Model','Provider model used for cleanup.', `<input class="input" id="aiModel" value="${escapeHTML(state.settings.modelName)}">`)}
          ${settingRow('Style','Default cleanup behavior.', `<select class="select" id="polishStyle"><option>Concise rewrite</option><option>Grammar only</option><option>Natural cleanup</option><option>Custom</option></select>`)}
        </div>
        <div style="margin-top:16px"><button class="button" id="testPolish" type="button">Send test polish</button></div>
      </section>` : ''}`;

    return `
      <section class="settings-section">
        <div class="settings-heading"><h2>System readiness</h2><p>Check the components Soundflow needs for private, offline dictation.</p></div>
        <div class="diagnostics">
          ${diagnosticRow('Model files','A local Whisper model is available.','models')}
          ${diagnosticRow('Microphone','An audio input is available for dictation.','microphone')}
          ${diagnosticRow('Global shortcut','Push-to-talk can work outside Soundflow.','shortcut')}
          ${diagnosticRow('Text insertion','Completed speech can be pasted at the cursor.','insertion')}
          ${diagnosticRow('Processing device','Recognition runs locally on this device.','device')}
        </div>
        <div style="display:flex; align-items:center; gap:12px; margin-top:18px; flex-wrap:wrap"><button class="button button--primary" id="runSystemCheck" type="button" ${state.systemStatus==='running'?'disabled':''}>${state.systemStatus==='running'?'<span class="spinner"></span> Checking…':'Run system check'}</button><span class="help">${state.systemStatus==='idle'?'Not checked yet':state.systemStatus==='running'?'Checking local components…':'All required components are ready.'}</span></div>
      </section>
      <section class="settings-section">
        <div class="settings-heading"><h2>Model location</h2><p>Recognition files are stored locally.</p></div>
        <input class="input path-field" value="/home/sha-weed/.local/share/soundflow/models/faster-whisper-small" readonly aria-label="Model location">
      </section>`;
  }

  function settingRow(name, description, control, disabled=false) {
    return `<div class="setting-row ${disabled?'is-disabled':''}" style="${disabled?'opacity:.48;pointer-events:none':''}"><div><div class="setting-name">${name}</div><div class="setting-description">${description}</div></div><div class="setting-control">${control}</div></div>`;
  }

  function switchHTML(id, checked) {
    return `<label class="switch" aria-label="${id}"><input type="checkbox" data-setting="${id}" ${checked?'checked':''}><span class="switch-track"></span></label>`;
  }

  const installedModels = new Set(['small']);
  function modelRow(id, description, recommended=false) {
    const name = id === 'large-v3-turbo' ? 'Large-v3 Turbo' : id.charAt(0).toUpperCase()+id.slice(1);
    const installed = installedModels.has(id);
    const selected = state.model === id;
    const downloading = state.downloads[id] != null && state.downloads[id] < 100;
    let action = '';
    if (downloading) {
      action = `<div class="progress" aria-label="Downloading ${name}"><span style="width:${state.downloads[id]}%"></span></div>`;
    } else if (installed) {
      action = selected ? `<span class="badge badge--success">In use</span>` : `<button class="button" type="button" data-use-model="${id}">Use</button>`;
    } else {
      action = `<button class="button" type="button" data-download-model="${id}">${icons('download')}Download</button>`;
    }
    return `<div class="model-row ${selected?'selected':''}"><div><div class="model-name">${name}${recommended?'<span class="badge badge--accent">Recommended</span>':''}</div><div class="model-description">${description}</div></div><div class="model-action">${action}</div></div>`;
  }

  function diagnosticRow(name, note, key) {
    let status;
    if (state.systemStatus === 'idle') status = `<span class="diagnostic-status">Not checked</span>`;
    else if (state.systemStatus === 'running') status = `<span class="diagnostic-status"><span class="spinner"></span>Checking</span>`;
    else status = `<span class="diagnostic-status ready">${icons('check')}Ready</span>`;
    return `<div class="diagnostic-row" data-diagnostic="${key}"><div><div class="diagnostic-name">${name}</div><div class="diagnostic-note">${note}</div></div>${status}</div>`;
  }

  function bindPreferenceControls(section) {
    document.querySelectorAll('[data-setting]').forEach(input => input.addEventListener('change', e => {
      const key = e.target.dataset.setting;
      if (key === 'aiEnabled') state.aiEnabled = e.target.checked;
      else if (key === 'autoPolish') state.autoPolish = e.target.checked;
      else state.settings[key] = e.target.checked;
      if (key === 'aiEnabled') { renderPreferences('ai-polish'); toast(state.aiEnabled ? 'AI Polish enabled. Transcript text may be sent to your provider.' : 'AI Polish disabled. Dictation is fully local.'); }
    }));

    document.querySelectorAll('[data-theme]').forEach(btn => btn.addEventListener('click', () => {
      state.settings.theme = btn.dataset.theme;
      if (state.settings.theme === 'light') {
        toast('Light theme preview is not included in this dark luxury concept.', 'info');
        state.settings.theme = 'dark';
      }
      renderPreferences('general');
    }));

    const timeout = document.querySelector('#timeoutRange');
    if (timeout) timeout.addEventListener('input', e => { state.settings.timeout = Number(e.target.value); e.target.closest('.setting-row').querySelector('.setting-description').textContent = `Finalize after about ${state.settings.timeout} ms of silence.`; });

    document.querySelectorAll('[data-download-model]').forEach(btn => btn.addEventListener('click', () => startModelDownload(btn.dataset.downloadModel)));
    document.querySelectorAll('[data-use-model]').forEach(btn => btn.addEventListener('click', () => { state.model = btn.dataset.useModel; renderPreferences('dictation'); toast(`${btn.dataset.useModel} model selected.`); }));

    const prefLanguage = document.querySelector('#prefLanguage');
    if (prefLanguage) { prefLanguage.value = state.settings.language; prefLanguage.addEventListener('change', e => state.settings.language=e.target.value); }

    const capture = document.querySelector('#shortcutCapture');
    if (capture) capture.addEventListener('click', () => { state.shortcutCapture = true; renderPreferences('shortcuts'); document.addEventListener('keydown', captureShortcut, {once:true}); });
    const reset = document.querySelector('#resetShortcut');
    if (reset) reset.addEventListener('click', () => { state.shortcut=['Ctrl','Alt','Space']; state.shortcutCapture=false; renderPreferences('shortcuts'); toast('Shortcut reset.'); });

    const toggleApi = document.querySelector('#toggleApi');
    if (toggleApi) toggleApi.addEventListener('click', () => { state.apiVisible=!state.apiVisible; renderPreferences('ai-polish'); });
    const provider = document.querySelector('#providerSelect');
    if (provider) { provider.value=state.settings.provider; provider.addEventListener('change', e=>state.settings.provider=e.target.value); }
    const model = document.querySelector('#aiModel');
    if (model) model.addEventListener('change', e=>state.settings.modelName=e.target.value);
    const polishStyle = document.querySelector('#polishStyle');
    if (polishStyle) { polishStyle.value=state.settings.style; polishStyle.addEventListener('change', e=>state.settings.style=e.target.value); }
    const test = document.querySelector('#testPolish');
    if (test) test.addEventListener('click', () => { test.disabled=true; test.innerHTML='<span class="spinner"></span> Testing…'; setTimeout(()=>{ toast('Provider connection succeeded.'); test.disabled=false; test.textContent='Send test polish'; },900); });

    const check = document.querySelector('#runSystemCheck');
    if (check) check.addEventListener('click', runSystemCheck);
  }

  function captureShortcut(e) {
    if (!state.shortcutCapture) return;
    e.preventDefault();
    const parts = [];
    if (e.ctrlKey) parts.push('Ctrl');
    if (e.altKey) parts.push('Alt');
    if (e.shiftKey) parts.push('Shift');
    if (e.metaKey) parts.push('Meta');
    const modifierKeys = ['Control','Alt','Shift','Meta'];
    if (!modifierKeys.includes(e.key)) parts.push(e.code === 'Space' ? 'Space' : (e.key.length===1 ? e.key.toUpperCase() : e.key));
    if (parts.length < 2) {
      toast('Use at least one modifier plus another key.', 'alert');
      document.addEventListener('keydown', captureShortcut, {once:true});
      return;
    }
    state.shortcut = parts;
    state.shortcutCapture=false;
    renderPreferences('shortcuts');
    toast('Shortcut updated.');
  }

  function startModelDownload(id) {
    state.downloads[id]=2;
    renderPreferences('dictation');
    const timer = setInterval(() => {
      state.downloads[id] = Math.min(100, state.downloads[id] + Math.floor(7 + Math.random()*14));
      const bar = document.querySelector(`[data-download-model="${id}"]`);
      if (location.hash !== '#/preferences/dictation') { clearInterval(timer); return; }
      if (state.downloads[id] >= 100) {
        clearInterval(timer);
        installedModels.add(id);
        state.downloads[id]=100;
        renderPreferences('dictation');
        toast(`${id} model downloaded.`);
      } else {
        renderPreferences('dictation');
      }
    }, 260);
  }

  function runSystemCheck() {
    state.systemStatus='running';
    renderPreferences('system');
    setTimeout(()=>{
      state.systemStatus='ready';
      renderPreferences('system');
      toast('System check complete. Soundflow is ready.');
    }, 1600);
  }

  function render() {
    updateNavigation();
    const [root, section] = route();
    if (root === 'history') renderHistory();
    else if (root === 'playground') renderPlayground();
    else if (root === 'preferences') renderPreferences(section || 'general');
    else renderDictation();
    app.focus({preventScroll:true});
  }

  window.addEventListener('hashchange', render);
  window.addEventListener('keydown', e => {
    if (e.key === 'Escape' && state.recording) {
      state.recording=false;
      clearInterval(state.recordTimer);
      state.recordTimer=null;
      render();
      toast('Dictation cancelled.', 'info');
    }
  });

  if (!location.hash) location.hash = '#/dictation';
  render();
})();
