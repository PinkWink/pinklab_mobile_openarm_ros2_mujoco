// Patrol dashboard front end: one EventSource (/api/stream) drives everything; cameras are plain MJPEG <img>.
const $ = (id) => document.getElementById(id);
const fmt = (v, d = 2, unit = "") => (v === null || v === undefined ? "-" : Number(v).toFixed(d) + unit);
const FOOT = [[0.38, 0.32], [0.38, -0.32], [-0.38, -0.32], [-0.38, 0.32]];

let S = null;            // latest state snapshot
let mapImg = null, mapMeta = null, mapVersion = null;
const cams = {};         // name -> {img, canvas, width, height}
let lastState = null, lastIndex = null, lastUnhelmeted = 0;

// ---------------------------------------------------------------- events
function log(text, cls = "") {
  const li = document.createElement("li");
  const t = S ? S.sim_time.toFixed(1) : "-";
  li.innerHTML = `<time>${t}s</time><span class="${cls}">${text}</span>`;
  $("log").prepend(li);
  while ($("log").children.length > 60) $("log").lastChild.remove();
}

// ---------------------------------------------------------------- map
async function loadMap() {
  const meta = await (await fetch("/api/map")).json();
  if (!meta.resolution) return;
  const img = new Image();
  img.src = "/api/map.png?v=" + meta.version;
  await img.decode();
  mapImg = img; mapMeta = meta;
}

function drawMap() {
  const cv = $("map"), ctx = cv.getContext("2d");
  const W = (cv.width = cv.clientWidth * devicePixelRatio), H = (cv.height = cv.clientHeight * devicePixelRatio);
  ctx.fillStyle = "#0b0f13"; ctx.fillRect(0, 0, W, H);
  if (!mapImg || !S) return;
  const m = mapMeta, mw = m.width * m.resolution, mh = m.height * m.resolution;
  const s = Math.min(W / mw, H / mh), ox = (W - mw * s) / 2, oy = (H - mh * s) / 2;
  const P = (x, y) => [ox + (x - m.origin[0]) * s, oy + mh * s - (y - m.origin[1]) * s];   // map metres → canvas px
  ctx.imageSmoothingEnabled = false;
  ctx.globalAlpha = 0.85; ctx.drawImage(mapImg, ox, oy, mw * s, mh * s); ctx.globalAlpha = 1;

  const line = (pts, color, width, dash = []) => {
    if (!pts || pts.length < 2) return;
    ctx.beginPath(); ctx.setLineDash(dash); ctx.strokeStyle = color; ctx.lineWidth = width;
    pts.forEach((p, i) => { const [x, y] = P(p[0], p[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.stroke(); ctx.setLineDash([]);
  };
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  line(S.trail, css("--truth") + "66", 2 * devicePixelRatio);
  line(S.plan, css("--plan"), 2.5 * devicePixelRatio, [6, 4]);

  // stops from the mission
  const stops = S.patrol ? S.patrol.stops : [];
  stops.forEach((st, i) => {
    const [x, y] = P(st.goal[0], st.goal[1]);
    ctx.beginPath(); ctx.arc(x, y, 9 * devicePixelRatio, 0, 7);
    ctx.fillStyle = st.status === "done" || st.status === "near" ? "#123b2a" : st.status === "active" ? "#16345a" : "#26313d"; ctx.fill();
    ctx.strokeStyle = st.status === "active" ? css("--truth") : "#56626f"; ctx.lineWidth = 1.5 * devicePixelRatio; ctx.stroke();
    ctx.fillStyle = "#e6edf3"; ctx.font = `${11 * devicePixelRatio}px sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(i + 1, x, y);
    ctx.textAlign = "left"; ctx.fillStyle = "#8b98a5"; ctx.fillText(st.label, x + 12 * devicePixelRatio, y);
  });

  ctx.fillStyle = css("--scan");
  (S.scan || []).forEach((p) => { const [x, y] = P(p[0], p[1]); ctx.fillRect(x - 1.5, y - 1.5, 3 * devicePixelRatio, 3 * devicePixelRatio); });

  (S.actors || []).forEach((a) => {
    const [x, y] = P(a.x, a.y);
    ctx.beginPath(); ctx.arc(x, y, 0.22 * s, 0, 7); ctx.fillStyle = a.helmet ? css("--person") : "#ff8787"; ctx.fill();
    ctx.strokeStyle = "#0b0f13"; ctx.lineWidth = 1; ctx.stroke();
  });

  const robot = (p, stroke, fill, width) => {
    if (!p) return;
    const [x, y, a] = p, c = Math.cos(a), sn = Math.sin(a);
    ctx.beginPath();
    FOOT.forEach(([fx, fy], i) => { const [X, Y] = P(x + c * fx - sn * fy, y + sn * fx + c * fy); i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); });
    ctx.closePath(); if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke();
    const [X0, Y0] = P(x, y), [X1, Y1] = P(x + 0.5 * c, y + 0.5 * sn);
    ctx.beginPath(); ctx.moveTo(X0, Y0); ctx.lineTo(X1, Y1); ctx.stroke();
  };
  robot(S.odom, css("--odom"), null, 1.5 * devicePixelRatio);
  robot(S.amcl, css("--amcl"), null, 2 * devicePixelRatio);
  robot(S.truth, css("--truth"), css("--truth") + "55", 2 * devicePixelRatio);
}

// ---------------------------------------------------------------- cameras
async function setupCameras() {
  const meta = await (await fetch("/api/cameras")).json();
  const names = Object.keys(meta);
  if (!names.length) { $("cams").innerHTML = '<div class="hint">카메라 프레임 없음: camera_handler:=…frame_tap.py:DashboardPipeline 로 띄웠는지 확인</div>'; return false; }
  $("cams").innerHTML = "";
  names.forEach((n) => {
    const box = document.createElement("div"); box.className = "cam";
    const img = document.createElement("img"); img.src = `/camera/${n}.mjpg?t=${Date.now()}`; img.alt = n;
    img.onerror = () => setTimeout(() => (img.src = `/camera/${n}.mjpg?t=${Date.now()}`), 1000);   // server restarted
    const canvas = document.createElement("canvas");
    const label = document.createElement("span"); label.className = "name"; label.textContent = n;
    box.append(img, canvas, label); $("cams").append(box);
    cams[n] = { img, canvas, width: meta[n].width, height: meta[n].height };
  });
  return true;
}

function drawDetections() {
  if (!S) return;
  for (const [name, c] of Object.entries(cams)) {
    const cv = c.canvas, ctx = cv.getContext("2d");
    cv.width = cv.clientWidth; cv.height = cv.clientHeight;
    const sx = cv.width / c.width, sy = cv.height / c.height;
    ctx.clearRect(0, 0, cv.width, cv.height);
    (S.detections[name] || []).forEach((d) => {
      const [x1, y1, x2, y2] = d.bbox;
      const person = d.label === "person";
      const noHelmet = person && d.attrs.helmet === "false";
      ctx.strokeStyle = noHelmet ? "#ff6b6b" : person ? "#ffd43b" : "#7ee787"; ctx.lineWidth = 2;
      ctx.strokeRect(x1 * sx, y1 * sy, (x2 - x1) * sx, (y2 - y1) * sy);
      ctx.font = "11px sans-serif"; ctx.fillStyle = ctx.strokeStyle;
      ctx.fillText(noHelmet ? "person · 안전모 X" : d.label, x1 * sx + 2, Math.max(11, y1 * sy - 3));
    });
  }
}

// ---------------------------------------------------------------- panels
function render() {
  $("simtime").textContent = fmt(S.sim_time, 1);
  $("rtf").textContent = fmt(S.rtf, 2);
  const [v, w] = S.twist || [];
  $("v").textContent = fmt(v, 2, " m/s"); $("w").textContent = fmt(w, 2, " rad/s");
  const err = (p) => (S.truth && p ? Math.hypot(p[0] - S.truth[0], p[1] - S.truth[1]) : null);
  $("erra").textContent = fmt(err(S.amcl), 3, " m"); $("erro").textContent = fmt(err(S.odom), 3, " m");
  $("cov").textContent = S.amcl_cov ? `${fmt(S.amcl_cov[0], 2)} m · ${fmt(S.amcl_cov[2], 1)}°` : "-";
  const seen = Object.values(S.detections || {}).flat().filter((d) => d.label === "person");
  $("people").textContent = `${seen.length} 명`;

  const p = S.patrol;
  if (!p) return;
  $("state").textContent = p.state; $("state").className = "state " + p.state;
  $("message").textContent = p.message;
  const done = p.stops.filter((s) => s.status === "done" || s.status === "near").length;
  $("bar").style.width = `${(100 * done) / Math.max(1, p.stops.length)}%`;
  $("elapsed").textContent = fmt(p.elapsed, 0, " s"); $("leg").textContent = fmt(p.leg_elapsed, 0, " s");
  $("remain").textContent = fmt(p.feedback && p.feedback.distance_remaining, 2, " m");
  $("recov").textContent = p.feedback && p.feedback.recoveries !== undefined ? p.feedback.recoveries : "-";
  $("stops").innerHTML = p.stops.map((s, i) => `<tr class="${s.status}"><td>${i + 1}</td><td>${s.label}</td>
      <td><span class="badge ${s.status}">${s.status}</span></td><td>${fmt(s.time, 1, " s")}</td>
      <td>${fmt(s.err_amcl, 3)}</td><td>${fmt(s.err_odom, 3)}</td></tr>`).join("");
  $("start").disabled = p.state !== "waiting"; $("cancel").disabled = p.state !== "running";

  if (p.state !== lastState) { log(`미션 상태: ${p.state}  ${p.message}`, p.state === "done" ? "ok" : p.state === "failed" || p.state === "canceled" ? "bad" : ""); lastState = p.state; }
  if (p.index !== lastIndex) {
    if (lastIndex !== null && lastIndex >= 0) {
      const s = p.stops[lastIndex];
      if (s && (s.status === "done" || s.status === "near"))
        log(`도착${s.status === "near" ? " (목표 근처에서 멈춤)" : ""}: ${s.label}  ${fmt(s.time, 1)} s · AMCL 오차 ${fmt(s.err_amcl, 3)} m · odom 오차 ${fmt(s.err_odom, 3)} m`, s.status === "near" ? "warn" : "ok");
    }
    if (p.index >= 0) log(`출발: ${p.stops[p.index].label} 로`);
    lastIndex = p.index;
  }
  const unhelmeted = seen.filter((d) => d.attrs.helmet === "false").length;
  if (unhelmeted && S.sim_time - lastUnhelmeted > 5) { log(`카메라: 안전모 미착용 ${unhelmeted} 명`, "warn"); lastUnhelmeted = S.sim_time; }
}

// ---------------------------------------------------------------- wiring
async function command(cmd) {
  const r = await fetch("/api/command", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cmd }) });
  log(`명령 전송: ${cmd} (${r.ok ? "ok" : "실패"})`, r.ok ? "" : "bad");
}
$("start").onclick = () => command("start");
$("cancel").onclick = () => command("cancel");

let camsReady = false, camsTried = 0;
const es = new EventSource("/api/stream");
let wasDown = false;
es.onopen = () => {
  $("conn").textContent = "연결됨"; $("conn").className = "chip on";
  if (wasDown) {           // the server came back: MJPEG connections died with it, reopen them
    Object.entries(cams).forEach(([n, c]) => (c.img.src = `/camera/${n}.mjpg?t=${Date.now()}`));
    mapVersion = null; wasDown = false;
  }
};
es.onerror = () => { $("conn").textContent = "끊김 (재연결 중)"; $("conn").className = "chip off"; wasDown = true; };
es.onmessage = async (e) => {
  S = JSON.parse(e.data);
  if (S.map_version && S.map_version !== mapVersion) { mapVersion = S.map_version; await loadMap(); }
  if (!camsReady && Date.now() - camsTried > 2000) { camsTried = Date.now(); camsReady = await setupCameras(); }
  render(); drawMap(); drawDetections();
};
window.addEventListener("resize", () => { drawMap(); drawDetections(); });
