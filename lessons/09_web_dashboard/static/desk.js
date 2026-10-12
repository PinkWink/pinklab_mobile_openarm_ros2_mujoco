// Lesson 09 instruction desk. Rides on lesson 04's app.js: same EventSource (es), same snapshot (S), same map.
const PHASE_KO = { idle: "대기", thinking: "LLM 계획 중", confirm: "확인 대기", running: "실행 중" };
let chatCount = 0, lastResult = null;

// ---------------------------------------------------------------- send one user turn
async function say(text) {
  text = text.trim();
  if (!text) return;
  const r = await fetch("/api/say", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
  if (!r.ok) log(`지령 거부: ${(await r.json()).error}`, "bad");
}
$("say").onsubmit = (e) => { e.preventDefault(); say($("text").value); $("text").value = ""; };
$("quick").onclick = (e) => { if (e.target.tagName === "BUTTON") say(e.target.textContent); };
$("task-cancel").onclick = () => fetch("/api/task_cancel", { method: "POST" });

// ---------------------------------------------------------------- task panel
function renderTask() {
  const t = S && S.task;
  if (!t) return;
  $("phase").textContent = PHASE_KO[t.phase] || t.phase;
  $("phase").className = "state " + ({ running: "running", confirm: "waiting", thinking: "running" }[t.phase] || "");
  $("cost").textContent = "$" + t.cost.toFixed(4);
  const busy = t.phase === "thinking" || t.phase === "running";
  $("send").disabled = busy; $("text").disabled = busy;
  $("task-cancel").disabled = t.phase !== "running";

  if (t.chat.length < chatCount) { $("chat").replaceChildren(); chatCount = 0; }   // the server restarted: start over
  if (t.chat.length !== chatCount) {                     // append only the new lines, keep the scroll at the bottom
    t.chat.slice(chatCount).forEach((c) => {
      const li = document.createElement("li"); li.className = c.who;
      li.innerHTML = `<time>${c.t.toFixed(1)}s</time><span></span>`;
      li.querySelector("span").textContent = c.text;    // text, not HTML: the reply comes from the LLM
      $("chat").append(li);
    });
    chatCount = t.chat.length;
    $("chat").scrollTop = $("chat").scrollHeight;
  }

  $("steps").replaceChildren(...t.steps.map((s) => {
    const li = document.createElement("li"); li.className = s.status;
    li.innerHTML = `<span class="badge ${s.status}">${s.status}</span> `;
    li.append(s.text);                                  // step notes come from the LLM: text, not HTML
    return li;
  }));
  const done = t.steps.filter((s) => s.status === "done").length;
  $("bar").style.width = `${(100 * done) / Math.max(1, t.steps.length)}%`;
  const f = t.feedback;
  $("detail").textContent = t.phase === "running" && f ? `${f.step + 1}/${f.total} ${f.action} · ${f.phase} · ${f.detail}` : "";

  const key = t.result && JSON.stringify(t.result);
  if (key && key !== lastResult) {
    lastResult = key;
    log(`계획 ${t.result.success ? "성공" : "실패"}: ${t.result.steps_done}/${t.steps.length} 단계 · ${t.result.spoken}`, t.result.success ? "ok" : "bad");
  }
}

// ---------------------------------------------------------------- planned places on lesson 04's map
const baseDrawMap = drawMap;
drawMap = function () {
  baseDrawMap();
  const t = S && S.task;
  if (!t || !mapImg || !t.steps.length) return;
  const cv = $("map"), ctx = cv.getContext("2d"), m = mapMeta;
  const mw = m.width * m.resolution, mh = m.height * m.resolution;
  const s = Math.min(cv.width / mw, cv.height / mh), ox = (cv.width - mw * s) / 2, oy = (cv.height - mh * s) / 2;
  const P = (x, y) => [ox + (x - m.origin[0]) * s, oy + mh * s - (y - m.origin[1]) * s];   // same transform as app.js
  const seen = new Set();
  t.steps.forEach((st) => {
    if (!st.goal || seen.has(st.place)) return;
    seen.add(st.place);
    const active = t.steps.some((o) => o.place === st.place && o.status === "active");
    const [x, y] = P(st.goal[0], st.goal[1]), r = 11 * devicePixelRatio;
    ctx.beginPath(); ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r); ctx.lineTo(x - r, y); ctx.closePath();
    ctx.fillStyle = active ? "#c084fc" : "#c084fc55"; ctx.fill();
    ctx.strokeStyle = "#c084fc"; ctx.lineWidth = 1.5 * devicePixelRatio; ctx.stroke();
    ctx.font = `bold ${12 * devicePixelRatio}px sans-serif`; ctx.textAlign = "left"; ctx.textBaseline = "middle";
    const tx = x + r + 5 * devicePixelRatio, tw = ctx.measureText(st.place).width, th = 18 * devicePixelRatio;
    ctx.fillStyle = "#0b0f13d9"; ctx.fillRect(tx - 4 * devicePixelRatio, y - th / 2, tw + 8 * devicePixelRatio, th);   // the map is light grey
    ctx.fillStyle = "#e9d5ff"; ctx.fillText(st.place, tx, y);
  });
};

es.addEventListener("message", renderTask);
