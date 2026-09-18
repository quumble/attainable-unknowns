(() => {
  'use strict';

  const app = document.getElementById('app');
  const now = () => new Date().toISOString();
  const perf = () => Math.round(performance.now());
  const params = new URLSearchParams(location.search);

  const state = {
    config: null,
    items: [],
    categories: null,
    permutations: null,
    mapCondition: null,
    interests: new Set(),
    trialQueue: [],
    trialIndex: 0,
    trialStartedAt: null,
    answerShownAt: null,
    currentTrial: null,
    session: {
      session_uuid: crypto.randomUUID ? crypto.randomUUID() : `session-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      study_version: null,
      started_at: now(),
      completed_at: null,
      prolific: {
        prolific_pid: params.get('PROLIFIC_PID'),
        study_id: params.get('STUDY_ID'),
        session_id: params.get('SESSION_ID')
      },
      map_condition: null,
      interest_selections: [],
      speed_motivation: null,
      trials: [],
      events: []
    }
  };

  function log(type, detail = {}) {
    state.session.events.push({ type, at: now(), t_ms: perf(), ...detail });
  }

  function shuffle(input) {
    const a = [...input];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function sample(input, n) { return shuffle(input).slice(0, n); }
  function esc(s) { const d=document.createElement('div'); d.textContent=String(s); return d.innerHTML; }

  async function loadJson(path) {
    const r = await fetch(path, { cache: 'no-store' });
    if (!r.ok) throw new Error(`${path}: ${r.status}`);
    return r.json();
  }

  async function init() {
    try {
      const [config, itemBank, categories, permutations] = await Promise.all([
        loadJson('config.json'),
        loadJson('../stimuli/items.json'),
        loadJson('../stimuli/category-maps.json'),
        loadJson('../stimuli/permutations.json')
      ]);
      state.config = config;
      state.items = itemBank.items;
      state.categories = categories;
      state.permutations = permutations;
      state.session.study_version = config.study_version;

      const override = params.get('map');
      state.mapCondition = ['broad','specific'].includes(override) ? override : (Math.random() < .5 ? 'broad' : 'specific');
      state.session.map_condition = state.mapCondition;
      log('session_loaded', { map_condition: state.mapCondition });
      renderIntro();
    } catch (err) {
      app.innerHTML = `<section class="panel"><h1>Attainable Unknowns</h1><p class="error">Could not load the pilot files.</p><p class="muted">Run this through a local or web server rather than opening index.html directly. ${esc(err.message)}</p></section>`;
    }
  }

  function renderIntro() {
    app.innerHTML = `<section class="panel">
      <div class="eyebrow">Pilot instrument ${esc(state.config.study_version)}</div>
      <h1>Attainable Unknowns</h1>
      <p>This short pilot is about which kinds of unanswered questions people choose to pursue. You will select interests, encounter six questions, and decide whether each answer creates another question worth following.</p>
      <p class="muted">This build stores responses only in this browser session unless you export them at the end. It does not yet transmit data to a server.</p>
      <div class="actions"><button class="button primary" id="begin">Begin pilot</button></div>
    </section>`;
    document.getElementById('begin').addEventListener('click', () => { log('intro_continue'); renderInterestMap(); });
  }

  function renderInterestMap() {
    const cats = state.categories[state.mapCondition];
    app.innerHTML = `<section class="panel">
      <div class="eyebrow">Interest map</div>
      <h2>What would you voluntarily choose to learn something about?</h2>
      <p class="muted">Choose as many or as few as genuinely catch you. There is no target number.</p>
      <div class="grid" id="interest-grid"></div>
      <div class="actions"><button class="button primary" id="interest-done">Continue</button></div>
    </section>`;
    const grid = document.getElementById('interest-grid');
    shuffle(cats).forEach(c => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'tile'; b.textContent = c.label; b.dataset.id = c.id; b.setAttribute('aria-pressed','false');
      b.addEventListener('click', () => {
        const selected = b.getAttribute('aria-pressed') === 'true';
        b.setAttribute('aria-pressed', String(!selected));
        if (selected) state.interests.delete(c.id); else state.interests.add(c.id);
        log('interest_toggle', { category_id:c.id, selected:!selected });
      });
      grid.appendChild(b);
    });
    document.getElementById('interest-done').addEventListener('click', prepareTrials);
  }

  function prepareTrials() {
    state.session.interest_selections = [...state.interests];
    const concrete = sample(state.items.filter(x => x.kind === 'concrete'), state.config.items_per_kind.concrete);
    const abstract = sample(state.items.filter(x => x.kind === 'abstract'), state.config.items_per_kind.abstract);
    state.trialQueue = shuffle([...concrete, ...abstract]);
    state.trialIndex = 0;
    log('interest_map_complete', { selected_count:state.interests.size, trial_item_ids:state.trialQueue.map(x=>x.id) });
    renderRootTrial();
  }

  function renderRootTrial() {
    if (state.trialIndex >= state.trialQueue.length) return renderExit();
    const item = state.trialQueue[state.trialIndex];
    const perm = state.permutations.branch_order_permutations[Math.floor(Math.random() * state.permutations.branch_order_permutations.length)];
    const ordered = perm.order.map(type => item.branches.find(b => b.type === type));
    state.currentTrial = {
      item,
      branch_order_id: perm.id,
      ordered_branches: ordered,
      opened: [],
      root_curiosity: state.config.root_curiosity_default,
      root_latency_ms: null,
      answer_to_first_branch_ms: null,
      stop_latency_ms: null
    };
    state.trialStartedAt = perf();
    state.answerShownAt = null;
    log('trial_start', { item_id:item.id, kind:item.kind, branch_order_id:perm.id });

    app.innerHTML = `<section class="panel">
      <div class="topline"><span class="pill">Question ${state.trialIndex + 1} of ${state.trialQueue.length}</span><span class="pill">${esc(item.kind)}</span></div>
      <div class="question">${esc(item.root_question)}</div>
      <div class="range-row"><label for="curiosity">How much do you want to know the answer?</label><strong id="curiosity-value">${state.config.root_curiosity_default}</strong></div>
      <input id="curiosity" type="range" min="0" max="100" value="${state.config.root_curiosity_default}">
      <div class="range-labels"><span>Not at all</span><span>Extremely</span></div>
      <div class="actions"><button class="button primary" id="show-answer">Show answer</button></div>
    </section>`;

    const slider = document.getElementById('curiosity');
    const value = document.getElementById('curiosity-value');
    slider.addEventListener('input', () => value.textContent = slider.value);
    document.getElementById('show-answer').addEventListener('click', () => {
      state.currentTrial.root_curiosity = Number(slider.value);
      state.currentTrial.root_latency_ms = perf() - state.trialStartedAt;
      log('root_answer_requested', { item_id:item.id, curiosity:Number(slider.value), latency_ms:state.currentTrial.root_latency_ms });
      renderAnswerAndBranches();
    });
  }

  function renderAnswerAndBranches() {
    const t = state.currentTrial;
    state.answerShownAt = perf();
    log('root_answer_shown', { item_id:t.item.id });
    app.innerHTML = `<section class="panel">
      <div class="topline"><span class="pill">Question ${state.trialIndex + 1} of ${state.trialQueue.length}</span><span class="pill">0 of ${state.config.max_branches_per_item} follow-ups</span></div>
      <div class="question">${esc(t.item.root_question)}</div>
      <div class="answer">${esc(t.item.root_answer)}</div>
      <hr>
      <h2>Did that answer create another question?</h2>
      <p class="muted">You may open up to two of these three. You can also stop here.</p>
      <div id="branches"></div>
      <div class="actions"><button class="button secondary" id="satisfied">I'm satisfied here</button></div>
    </section>`;
    const holder = document.getElementById('branches');
    t.ordered_branches.forEach((b, position) => {
      const wrap = document.createElement('div');
      const btn = document.createElement('button');
      btn.type='button'; btn.className='branch'; btn.textContent=b.question; btn.dataset.branchId=b.id;
      const ans = document.createElement('div'); ans.className='branch-answer'; ans.hidden=true; ans.textContent=b.answer;
      btn.addEventListener('click', () => openBranch(b, position, btn, ans));
      wrap.append(btn,ans); holder.appendChild(wrap);
    });
    document.getElementById('satisfied').addEventListener('click', finishTrial);
  }

  function openBranch(branch, position, btn, ans) {
    const t = state.currentTrial;
    if (t.opened.length >= state.config.max_branches_per_item || t.opened.some(x => x.id === branch.id)) return;
    const latency = state.answerShownAt ? perf() - state.answerShownAt : null;
    if (t.opened.length === 0) t.answer_to_first_branch_ms = latency;
    t.opened.push({ id:branch.id, type:branch.type, position, selected_at:now(), latency_from_root_answer_ms:latency });
    btn.disabled = true; btn.textContent = 'Opened'; ans.hidden = false;
    log('branch_opened', { item_id:t.item.id, branch_id:branch.id, branch_type:branch.type, position, depth:t.opened.length, latency_from_root_answer_ms:latency });

    const pill = app.querySelector('.topline .pill:last-child');
    pill.textContent = `${t.opened.length} of ${state.config.max_branches_per_item} follow-ups`;
    if (t.opened.length >= state.config.max_branches_per_item) {
      app.querySelectorAll('.branch:not(:disabled)').forEach(x => { x.disabled=true; x.textContent='Not available'; });
      document.getElementById('satisfied').textContent = 'Continue';
    } else {
      document.getElementById('satisfied').textContent = 'Stop here';
    }
  }

  function finishTrial() {
    const t = state.currentTrial;
    t.stop_latency_ms = state.answerShownAt ? perf() - state.answerShownAt : null;
    state.session.trials.push({
      item_id:t.item.id,
      item_kind:t.item.kind,
      broad_category:t.item.broad_category,
      specific_category:t.item.specific_category,
      root_curiosity:t.root_curiosity,
      root_latency_ms:t.root_latency_ms,
      branch_order_id:t.branch_order_id,
      branch_order:t.ordered_branches.map(x=>x.type),
      branches_opened:t.opened,
      branch_depth:t.opened.length,
      stop_latency_ms:t.stop_latency_ms
    });
    log('trial_complete', { item_id:t.item.id, branch_depth:t.opened.length, branch_types:t.opened.map(x=>x.type) });
    state.trialIndex += 1;
    renderRootTrial();
  }

  function renderExit() {
    app.innerHTML = `<section class="panel">
      <div class="eyebrow">One final calibration</div>
      <h2>While doing this study, how much were you trying to finish as quickly as possible?</h2>
      <div class="range-row"><span>Speed motivation</span><strong id="speed-value">50</strong></div>
      <input id="speed" type="range" min="0" max="100" value="50">
      <div class="range-labels"><span>Not at all</span><span>As much as possible</span></div>
      <div class="actions"><button class="button primary" id="complete">Complete pilot</button></div>
    </section>`;
    const slider=document.getElementById('speed'); const value=document.getElementById('speed-value');
    slider.addEventListener('input',()=>value.textContent=slider.value);
    document.getElementById('complete').addEventListener('click',()=>{
      state.session.speed_motivation=Number(slider.value);
      state.session.completed_at=now();
      log('session_complete',{speed_motivation:state.session.speed_motivation});
      completeSession();
    });
  }

  async function completeSession() {
    let submission = 'local_export';
    if (state.config.submission_endpoint) {
      try {
        const r = await fetch(state.config.submission_endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(state.session)});
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        submission='posted';
      } catch (err) {
        submission='post_failed';
        log('submission_failed',{message:String(err.message||err)});
      }
    }
    renderSummary(submission);
  }

  function aggregate() {
    const depths=state.session.trials.map(t=>t.branch_depth);
    const branchCounts={explanation:0,boundary:0,implication:0};
    state.session.trials.forEach(t=>t.branches_opened.forEach(b=>branchCounts[b.type]++));
    return {
      mean_root_curiosity: depths.length ? Math.round(state.session.trials.reduce((a,t)=>a+t.root_curiosity,0)/depths.length) : 0,
      total_followups: depths.reduce((a,b)=>a+b,0),
      zero_depth_items: depths.filter(x=>x===0).length,
      one_depth_items: depths.filter(x=>x===1).length,
      two_depth_items: depths.filter(x=>x===2).length,
      branch_counts:branchCounts
    };
  }

  function renderSummary(submission) {
    const a=aggregate();
    const summaryVisible=state.config.show_pilot_summary;
    app.innerHTML = `<section class="panel">
      <div class="eyebrow">Pilot complete</div>
      <h1>Thank you.</h1>
      ${summaryVisible ? `<div class="notice"><strong>Test-pilot summary</strong><br>Mean root curiosity: ${a.mean_root_curiosity}/100<br>Total follow-ups opened: ${a.total_followups}<br>Depth 0 / 1 / 2: ${a.zero_depth_items} / ${a.one_depth_items} / ${a.two_depth_items}<br>Branch choices — explanation: ${a.branch_counts.explanation}, boundary: ${a.branch_counts.boundary}, implication: ${a.branch_counts.implication}</div>` : ''}
      <p class="muted">Submission mode: ${esc(submission)}. Until a storage endpoint is configured, use the export button to preserve this session.</p>
      <div class="actions"><button class="button secondary" id="export">Export session JSON</button>${state.config.completion_url ? '<button class="button primary" id="return">Return to Prolific</button>' : ''}</div>
    </section>`;
    document.getElementById('export').addEventListener('click',exportSession);
    const ret=document.getElementById('return'); if(ret) ret.addEventListener('click',()=>location.href=state.config.completion_url);
  }

  function exportSession() {
    const blob=new Blob([JSON.stringify(state.session,null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob); const a=document.createElement('a');
    a.href=url; a.download=`attainable-unknowns-${state.session.session_uuid}.json`; a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    log('session_exported');
  }

  init();
})();
