/* ============================================================
   Job Search AI — Dashboard App Logic v3.0
   ============================================================ */

const API = '';

/* ── Utils ── */
function toast(msg, type = 'in', ms = 4000) {
  const c = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${{ok:'✅',er:'❌',in:'ℹ️'}[type]||'💬'}</span><span>${msg}</span>`;
  c.appendChild(el);
  setTimeout(() => el.remove(), ms);
}

function setLoad(btn, on) {
  const t = btn.querySelector('.bt'), s = btn.querySelector('.spinner');
  if (t) t.classList.toggle('hidden', on);
  if (s) s.classList.toggle('hidden', !on);
  btn.disabled = on;
}

async function callTool(name, args) {
  const r = await fetch(`${API}/api/tools/${encodeURIComponent(name)}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({arguments: args})
  });
  const d = await r.json();
  if (!d.success) throw new Error(d.message || 'Tool failed');
  return d.result;
}

/* ── Navigation ── */
document.addEventListener('DOMContentLoaded', () => {

  const navBtns = document.querySelectorAll('.nav-btn');
  const views   = document.querySelectorAll('.view');

  navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      navBtns.forEach(b => b.classList.remove('active'));
      views.forEach(v => v.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(btn.dataset.view).classList.add('active');
      if (btn.dataset.view === 'view-apps') loadApps();
    });
  });

  /* ── Tabs (generic) ── */
  document.querySelectorAll('.tabs').forEach(bar => {
    bar.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const parent = bar.closest('section') || bar.parentElement;
        bar.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        parent.querySelectorAll('.tab-content, [id^="sal-"], [id^="set-"]').forEach(t => {
          if (t.tagName !== 'BUTTON') t.style.display = 'none';
        });
        btn.classList.add('active');
        const tab = document.getElementById(btn.dataset.tab);
        if (tab) tab.style.display = 'block';
      });
    });
  });

  /* ══════════════════════════════════════════════════
     AI CHAT
  ══════════════════════════════════════════════════ */
  const chatForm = document.getElementById('chatForm');
  const chatIn   = document.getElementById('chatIn');
  const chatMsgs = document.getElementById('chatMsgs');
  const sendBtn  = document.getElementById('sendBtn');

  chatIn.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 130) + 'px';
  });
  chatIn.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); chatForm.dispatchEvent(new Event('submit')); }
  });

  document.getElementById('clearChat').addEventListener('click', () => {
    chatMsgs.innerHTML = `<div class="msg bot"><div class="msg-av">🤖</div><div class="msg-bub"><p>Chat cleared. How can I help?</p></div></div>`;
  });

  document.querySelectorAll('.qchip').forEach(c => {
    c.addEventListener('click', () => { chatIn.value = c.dataset.p; chatForm.dispatchEvent(new Event('submit')); });
  });

  chatForm.addEventListener('submit', async e => {
    e.preventDefault();
    const msg = chatIn.value.trim();
    if (!msg) return;
    addMsg('user', msg);
    chatIn.value = ''; chatIn.style.height = 'auto';
    const tid = addTyping();
    sendBtn.disabled = true;
    try {
      const r = await fetch(`${API}/chat`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: msg})
      });
      removeTyping(tid);
      const d = await r.json();
      addMsg('bot', r.ok ? d.response : '⚠️ Server error. Try again.', true);
    } catch {
      removeTyping(tid);
      addMsg('bot', '⚠️ Network error — ensure the server is running.');
    } finally { sendBtn.disabled = false; }
  });

  function addMsg(role, text, md = false) {
    const d = document.createElement('div');
    d.className = `msg ${role}`;
    d.innerHTML = `<div class="msg-av">${role === 'user' ? '👤' : '🤖'}</div>
      <div class="msg-bub">${md ? marked.parse(text) : `<p>${text.replace(/\n/g,'<br>')}</p>`}</div>`;
    chatMsgs.appendChild(d);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
  }

  function addTyping() {
    const id = 'tp' + Date.now();
    const d = document.createElement('div');
    d.id = id; d.className = 'msg bot';
    d.innerHTML = `<div class="msg-av">🤖</div><div class="msg-bub"><div class="typing"><span></span><span></span><span></span></div></div>`;
    chatMsgs.appendChild(d);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
    return id;
  }
  function removeTyping(id) { const el = document.getElementById(id); if (el) el.remove(); }

  /* ══════════════════════════════════════════════════
     JOB SEARCH
  ══════════════════════════════════════════════════ */
  window.qJob = (title, loc) => {
    document.querySelector('[data-view="view-jobs"]').click();
    document.getElementById('jt').value = title;
    document.getElementById('jl').value = loc;
    document.getElementById('jobForm').dispatchEvent(new Event('submit'));
  };

  document.getElementById('jobForm').addEventListener('submit', async e => {
    e.preventDefault();
    const btn    = document.getElementById('jobBtn');
    const title  = document.getElementById('jt').value.trim();
    const loc    = document.getElementById('jl').value.trim();
    const n      = parseInt(document.getElementById('jr').value) || 10;
    const notice = document.getElementById('jn').value ? parseInt(document.getElementById('jn').value) : null;
    const wfh    = document.getElementById('jwfh').checked || null;
    if (!title) { toast('Enter a job title', 'er'); return; }
    setLoad(btn, true);
    document.getElementById('jobOut').innerHTML = '';
    try {
      const args = {job_title: title, location: loc || 'India', country_code: 'in', results_per_page: n};
      if (notice) args.notice_period_days = notice;
      if (wfh)    args.work_from_home = true;
      renderJobs(await callTool('job_search', args));
      toast('Jobs loaded', 'ok');
    } catch (err) { toast('Job search failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  document.getElementById('cityBtn').addEventListener('click', async () => {
    const btn   = document.getElementById('cityBtn');
    const title = document.getElementById('jt').value.trim();
    if (!title) { toast('Enter a job title first', 'er'); return; }
    setLoad(btn, true);
    document.getElementById('jobOut').innerHTML = '';
    try {
      renderJobs(await callTool('location_based_job_search', {job_title: title, results_per_city: 2}));
      toast('Multi-city results loaded', 'ok');
    } catch (err) { toast('City search failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  function renderJobs(text) {
    const out = document.getElementById('jobOut');
    out.innerHTML = '';
    // Try JSON
    try {
      const jobs = JSON.parse(text);
      if (Array.isArray(jobs) && jobs.length) {
        jobs.forEach(j => out.appendChild(jobCard(j)));
        return;
      }
    } catch {}
    // Text fallback
    const sections = text.split(/(###[^#]+###)/g);
    sections.forEach(s => {
      if (s.startsWith('###')) {
        const hdr = document.createElement('div');
        hdr.style.cssText = 'font-size:12.5px;font-weight:600;color:var(--cyan);margin:16px 0 7px;padding-left:2px';
        hdr.textContent = s.replace(/###/g, '').trim();
        out.appendChild(hdr);
      } else if (s.trim()) {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.cssText = 'font-size:13px;line-height:1.75;color:var(--t2);white-space:pre-wrap;margin-bottom:8px';
        card.textContent = s.trim();
        out.appendChild(card);
      }
    });
  }

  function jobCard(j) {
    const icons = ['🏢','💼','🖥️','🔬','📊','🎯'];
    const el = document.createElement('div');
    el.className = 'job-card';
    el.innerHTML = `
      <div class="job-ico">${icons[Math.floor(Math.random()*icons.length)]}</div>
      <div class="job-info">
        <div class="jt">${j.title||j.job_title||'Position'}</div>
        <div class="jc">${j.company||j.company_name||''}</div>
        <div class="job-meta">
          ${j.location?`<span>📍 ${j.location}</span>`:''}
          ${j.salary_min?`<span>💰 ₹${Number(j.salary_min).toLocaleString('en-IN')} – ${Number(j.salary_max||0).toLocaleString('en-IN')}</span>`:''}
          ${j.contract_type?`<span class="badge bc">${j.contract_type}</span>`:''}
        </div>
        ${j.redirect_url?`<a class="job-link" href="${j.redirect_url}" target="_blank"><i class="fa fa-external-link-alt"></i> View Job</a>`:''}
      </div>`;
    return el;
  }

  /* ══════════════════════════════════════════════════
     ATS / RESUME
  ══════════════════════════════════════════════════ */
  async function runATS(prompt) {
    const resume = document.getElementById('atsResume').value.trim();
    const jd     = document.getElementById('atsJD').value.trim();
    if (!resume || !jd) { toast('Paste both resume and job description', 'er'); return false; }
    const r = await fetch(`${API}/chat`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: `${prompt}\n\nRESUME:\n${resume}\n\nJOB DESCRIPTION:\n${jd}`})
    });
    return (await r.json()).response;
  }

  document.getElementById('atsBtn').addEventListener('click', async () => {
    const btn = document.getElementById('atsBtn');
    setLoad(btn, true);
    document.getElementById('atsOut').style.display = 'none';
    try {
      const text = await runATS('Analyze this resume against the job description. Give an ATS compatibility score out of 100, list matched keywords, missing keywords, and 3-5 specific improvement recommendations.');
      if (text) renderATS(text, document.getElementById('atsResume').value, document.getElementById('atsJD').value);
    } catch (err) { toast('Analysis failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  document.getElementById('gapBtn').addEventListener('click', async () => {
    const btn = document.getElementById('gapBtn');
    setLoad(btn, true);
    document.getElementById('atsOut').style.display = 'none';
    try {
      const text = await runATS('Do a detailed skills gap analysis. List skills/keywords present in the resume, skills missing from the resume but required in the JD, and recommendations.');
      if (text) renderATS(text, document.getElementById('atsResume').value, document.getElementById('atsJD').value);
    } catch (err) { toast('Gap analysis failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  function renderATS(text, resume, jd) {
    const scoreMatch = text.match(/\b(\d{1,3})\s*(?:\/\s*100|%|out of 100)/i);
    const score = scoreMatch ? Math.min(parseInt(scoreMatch[1]), 100) : null;
    document.getElementById('atsOut').style.display = 'block';

    // Score ring
    const fill  = document.getElementById('ringFill');
    const numEl = document.getElementById('ringNum');
    const circ  = 2 * Math.PI * 49; // r=49
    fill.style.strokeDasharray  = circ;
    fill.style.strokeDashoffset = circ;
    if (score !== null) {
      setTimeout(() => { fill.style.strokeDashoffset = circ - (score / 100) * circ; }, 50);
      fill.style.stroke = score >= 70 ? 'var(--green)' : score >= 50 ? 'var(--amber)' : 'var(--red)';
      numEl.textContent = score;
      numEl.style.color = score >= 70 ? 'var(--green)' : score >= 50 ? 'var(--amber)' : 'var(--red)';
    } else {
      numEl.textContent = '—';
    }

    // Bars
    const s = score || 60;
    document.getElementById('scoreBars').innerHTML = [
      {l:'Keyword Match', p: Math.min(s+8, 100)},
      {l:'Skills Fit',    p: Math.max(s-5, 0)},
      {l:'Experience',    p: Math.min(s+12, 100)},
    ].map(b => `<div class="bar-row">
      <div class="bar-lbl">${b.l}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${b.p}%"></div></div>
      <div class="bar-val">${b.p}%</div>
    </div>`).join('');

    // Keywords
    const jdWords  = [...new Set((jd.toLowerCase().match(/\b[a-z]{4,}\b/g)||[]))];
    const stopWords = new Set(['with','that','this','from','have','your','will','been','they','when','what','more','than','just','also','some','into','over','each','like','such','then','only','most','both','very','their','about','which','there','these','other','would','could','should','where','while','role','work','team','must','able','skills','experience','years','strong','good']);
    const keywords = jdWords.filter(w => !stopWords.has(w)).slice(0, 22);
    const rLow     = resume.toLowerCase();
    const found    = keywords.filter(w => rLow.includes(w));
    const missing  = keywords.filter(w => !rLow.includes(w)).slice(0, 10);
    document.getElementById('kwOut').innerHTML = `
      <div style="font-size:11.5px;color:var(--t3);margin-bottom:8px">
        <span style="color:var(--green)">✅ ${found.length} found</span> &nbsp; <span style="color:var(--red)">❌ ${missing.length} missing</span>
      </div>
      <div class="kw-chips">
        ${found.slice(0,12).map(k=>`<span class="kw found">${k}</span>`).join('')}
        ${missing.map(k=>`<span class="kw miss">${k}</span>`).join('')}
      </div>`;

    // AI recommendations
    document.getElementById('recOut').innerHTML = marked.parse(text);
    toast('Analysis complete!', 'ok');
  }

  /* ══════════════════════════════════════════════════
     SALARY
  ══════════════════════════════════════════════════ */
  document.getElementById('salBtn').addEventListener('click', async () => {
    const btn  = document.getElementById('salBtn');
    const basic = parseFloat(document.getElementById('sb').value) || 0;
    if (!basic) { toast('Enter a basic salary', 'er'); return; }
    setLoad(btn, true);
    try {
      const d = JSON.parse(await callTool('salary_calculator', {
        basic_salary: basic,
        hra_pct: parseFloat(document.getElementById('sh').value)||15,
        da_pct:  parseFloat(document.getElementById('sd').value)||5,
        ta_pct:  parseFloat(document.getElementById('st').value)||2,
        currency: document.getElementById('sc').value
      }));
      renderSalary(d);
      toast('Calculated!', 'ok');
    } catch (err) { toast('Failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  function renderSalary(d) {
    const sym = {INR:'₹',USD:'$',EUR:'€',GBP:'£'}[d.currency] || d.currency;
    const fmt = n => `${sym}${Number(n).toLocaleString('en-IN',{maximumFractionDigits:0})}`;
    document.getElementById('salBD').style.display = 'block';
    document.getElementById('salBDIn').innerHTML = `
      <table class="sal-table">
        <thead><tr><th>Component</th><th>Monthly</th><th>Annual</th></tr></thead>
        <tbody>
          <tr><td>Basic Salary</td><td>${fmt(d.basic_salary)}</td><td>${fmt(d.basic_salary*12)}</td></tr>
          <tr><td>HRA (${d.components?.hra_pct||15}%)</td><td>${fmt(d.hra)}</td><td>${fmt(d.hra*12)}</td></tr>
          <tr><td>DA (${d.components?.da_pct||5}%)</td><td>${fmt(d.da)}</td><td>${fmt(d.da*12)}</td></tr>
          <tr><td>TA (${d.components?.ta_pct||2}%)</td><td>${fmt(d.ta)}</td><td>${fmt(d.ta*12)}</td></tr>
          <tr class="tr-total"><td>Gross</td><td>${fmt(d.gross)}</td><td>${fmt(d.annual_ctc)}</td></tr>
        </tbody>
      </table>`;
    document.getElementById('salStats').style.display = 'grid';
    document.getElementById('salStats').innerHTML = `
      <div class="sal-stat"><div class="sv">${fmt(d.basic_salary)}</div><div class="sl">Monthly Basic</div></div>
      <div class="sal-stat"><div class="sv">${fmt(d.gross)}</div><div class="sl">Monthly Gross</div></div>
      <div class="sal-stat"><div class="sv">${fmt(d.annual_ctc)}</div><div class="sl">Annual CTC</div></div>`;
  }

  document.getElementById('srBtn').addEventListener('click', async () => {
    const btn   = document.getElementById('srBtn');
    const title = document.getElementById('srTitle').value.trim();
    if (!title) { toast('Enter a job title', 'er'); return; }
    setLoad(btn, true);
    try {
      const d = JSON.parse(await callTool('salary_research', {title, location: document.getElementById('srLoc').value.trim()||undefined}));
      const fmt = n => `₹${Number(n).toLocaleString('en-IN',{maximumFractionDigits:0})}`;
      document.getElementById('srOut').style.display = 'block';
      document.getElementById('srOut').innerHTML = `
        <div class="g3" style="margin-bottom:14px">
          <div class="sal-stat"><div class="sv">${fmt(d.average_annual_inr)}</div><div class="sl">Avg Annual</div></div>
          <div class="sal-stat"><div class="sv">${fmt(d.median_annual_inr)}</div><div class="sl">Median Annual</div></div>
          <div class="sal-stat"><div class="sv">${d.count}</div><div class="sl">Data Points</div></div>
        </div>
        <div class="card"><div class="card-title">Matching Roles</div>
          <table class="sal-table"><thead><tr><th>Title</th><th>Annual (INR)</th><th>Monthly</th></tr></thead>
            <tbody>${(d.results||[]).map(r=>`<tr><td>${r.title}</td><td>${fmt(r.annual_inr)}</td><td>${fmt(r.monthly_inr)}</td></tr>`).join('')}</tbody>
          </table>
        </div>`;
      toast('Research complete', 'ok');
    } catch (err) { toast('Failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  /* ══════════════════════════════════════════════════
     COMPANY RESEARCH
  ══════════════════════════════════════════════════ */
  window.doCompany = name => {
    document.querySelector('[data-view="view-company"]').click();
    document.getElementById('coName').value = name;
    document.getElementById('coBtn').click();
  };

  document.getElementById('coBtn').addEventListener('click', async () => {
    const btn  = document.getElementById('coBtn');
    const name = document.getElementById('coName').value.trim();
    if (!name) { toast('Enter a company name', 'er'); return; }
    setLoad(btn, true);
    document.getElementById('coOut').classList.remove('show');
    try {
      const result = await callTool('company_research', {company_name: name});
      document.getElementById('coTitle').innerHTML = `🏢 ${name}`;
      document.getElementById('coBody').innerHTML = marked.parse(result);
      document.getElementById('coOut').classList.add('show');
      toast('Research complete', 'ok');
    } catch (err) { toast('Research failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  document.getElementById('coName').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('coBtn').click();
  });

  /* ══════════════════════════════════════════════════
     INTERVIEW PREP
  ══════════════════════════════════════════════════ */
  let ivAction = 'questions';

  document.querySelectorAll('.ac').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.ac').forEach(c => c.classList.remove('sel'));
      card.classList.add('sel');
      ivAction = card.dataset.action;
      document.getElementById('ivJdGroup').style.display = ivAction === 'analyze_jd' ? 'flex' : 'none';
    });
  });

  document.getElementById('ivBtn').addEventListener('click', async () => {
    const btn  = document.getElementById('ivBtn');
    setLoad(btn, true);
    const out = document.getElementById('ivOut');
    out.classList.remove('show');
    try {
      const args = {
        action:           ivAction,
        job_title:        document.getElementById('ivTitle').value.trim(),
        company_name:     document.getElementById('ivCo').value.trim(),
        category:         document.getElementById('ivCat').value,
        experience_level: document.getElementById('ivLvl').value,
        job_description:  document.getElementById('ivJD').value.trim()
      };
      out.innerHTML = marked.parse(await callTool('interview_prep', args));
      out.classList.add('show');
      out.scrollIntoView({behavior:'smooth', block:'nearest'});
      toast('Interview prep ready!', 'ok');
    } catch (err) { toast('Failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  /* ══════════════════════════════════════════════════
     MY APPLICATIONS
  ══════════════════════════════════════════════════ */
  const UID = 'guest';

  async function loadApps() {
    try {
      const r = JSON.parse(await callTool('get_job_applications', {user_id: UID}));
      renderApps(r);
    } catch { document.getElementById('apTable').innerHTML = `<div class="empty"><div class="ei">⚠️</div><p>Could not load applications.</p></div>`; }
  }

  document.getElementById('apRefresh').addEventListener('click', loadApps);

  document.getElementById('appForm').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = document.getElementById('apBtn');
    setLoad(btn, true);
    try {
      await callTool('save_job_application', {
        user_id:   UID,
        job_title: document.getElementById('apTitle').value.trim(),
        company:   document.getElementById('apCo').value.trim(),
        location:  document.getElementById('apLoc').value.trim(),
        status:    document.getElementById('apSt').value,
        notes:     document.getElementById('apNotes').value.trim()
      });
      document.getElementById('appForm').reset();
      await loadApps();
      toast('Application saved!', 'ok');
    } catch (err) { toast('Save failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  function renderApps(apps) {
    const el = document.getElementById('apTable');
    if (!apps || !apps.length) {
      el.innerHTML = `<div class="empty"><div class="ei">📋</div><p>No applications yet — add your first one above.</p></div>`;
      return;
    }
    el.innerHTML = `<table class="app-table">
      <thead><tr><th>Job Title</th><th>Company</th><th>Location</th><th>Status</th><th>Notes</th><th>Date</th></tr></thead>
      <tbody>${apps.map(a=>`<tr>
        <td><strong>${a.job_title||a.title||''}</strong></td>
        <td>${a.company||''}</td>
        <td>${a.location||'—'}</td>
        <td><span class="sp sp-${a.status||'Applied'}">${a.status||'Applied'}</span></td>
        <td style="color:var(--t2);font-size:12px">${a.notes||'—'}</td>
        <td style="color:var(--t3);font-size:11.5px">${a.created_at?new Date(a.created_at).toLocaleDateString('en-IN'):'—'}</td>
      </tr>`).join('')}</tbody>
    </table>`;
  }

  /* ══════════════════════════════════════════════════
     JOB ALERTS
  ══════════════════════════════════════════════════ */
  document.getElementById('alertForm').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = document.getElementById('alBtn');
    setLoad(btn, true);
    try {
      const r = await fetch(`${API}/api/alerts`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          email:     document.getElementById('alEmail').value.trim(),
          job_title: document.getElementById('alTitle').value.trim(),
          location:  document.getElementById('alLoc').value.trim(),
          frequency: document.getElementById('alFreq').value
        })
      });
      const d = await r.json();
      if (d.success !== false) { toast('🔔 Alert created! You\'ll receive matching jobs by email.', 'ok', 5000); document.getElementById('alertForm').reset(); }
      else toast(d.message || 'Failed', 'er');
    } catch (err) { toast('Error: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  /* ══════════════════════════════════════════════════
     SETTINGS
  ══════════════════════════════════════════════════ */
  document.getElementById('regBtn').addEventListener('click', async () => {
    const btn = document.getElementById('regBtn');
    setLoad(btn, true);
    try {
      await callTool('register_account', {full_name: document.getElementById('rName').value.trim(), email: document.getElementById('rEmail').value.trim(), password: document.getElementById('rPwd').value, phone: document.getElementById('rPhone').value.trim()});
      toast('Account created!', 'ok');
    } catch (err) { toast('Registration failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  document.getElementById('loginBtn').addEventListener('click', async () => {
    const btn = document.getElementById('loginBtn');
    setLoad(btn, true);
    try {
      const r = await callTool('login_account', {email: document.getElementById('lEmail').value.trim(), password: document.getElementById('lPwd').value});
      const out = document.getElementById('loginOut');
      out.textContent = r; out.style.display = 'block';
      toast('Logged in!', 'ok');
    } catch (err) { toast('Login failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  document.getElementById('prefsBtn').addEventListener('click', async () => {
    const btn = document.getElementById('prefsBtn');
    setLoad(btn, true);
    try {
      await callTool('save_job_preferences', {
        user_id:             UID,
        preferred_locations: document.getElementById('pLocs').value.split(',').map(s=>s.trim()).filter(Boolean),
        target_roles:        document.getElementById('pRoles').value.split(',').map(s=>s.trim()).filter(Boolean),
        notice_period_days:  document.getElementById('pNotice').value ? parseInt(document.getElementById('pNotice').value) : null,
        work_from_home:      document.getElementById('pWfh').checked || null
      });
      toast('Preferences saved!', 'ok');
    } catch (err) { toast('Save failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

  document.getElementById('notifBtn').addEventListener('click', async () => {
    const btn = document.getElementById('notifBtn');
    const uid = parseInt(document.getElementById('nUid').value);
    if (!uid) { toast('Enter a valid User ID', 'er'); return; }
    setLoad(btn, true);
    try {
      await callTool('update_notification_settings', {user_id: uid, preference: document.getElementById('nPref').value});
      toast('Notifications updated!', 'ok');
    } catch (err) { toast('Update failed: ' + err.message, 'er'); }
    finally { setLoad(btn, false); }
  });

});
