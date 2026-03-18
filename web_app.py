import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_file

from audio_pipeline import PipelineConfig, enhance_file

app = Flask(__name__)

SUPPORTED_EXTS = {".mp3", ".wav", ".flac"}
APP_NAME = "MasterForge 320"

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>MasterForge 320</title>
  <style>
    :root {
      --bg: #0f172a;
      --card: #111827;
      --text: #e5e7eb;
      --muted: #94a3b8;
      --accent: #22c55e;
      --accent-hover: #16a34a;
      --line: #334155;
      --input: #0b1220;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      padding: 24px;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", Arial, sans-serif;
    }

    .wrap {
      max-width: 760px;
      margin: 0 auto;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 700;
    }

    .sub {
      margin: 6px 0 16px;
      color: var(--muted);
    }

    .card {
      background: var(--card);
      border-radius: 12px;
      padding: 16px;
      border: 1px solid var(--line);
    }

    label {
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
      color: var(--text);
    }

    .row {
      display: flex;
      gap: 8px;
      margin-bottom: 10px;
    }

    input[type=file], select {
      width: 100%;
      background: var(--input);
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      margin-bottom: 12px;
    }

    #drop {
      border: 1px dashed var(--line);
      border-radius: 10px;
      background: var(--input);
      color: #cbd5e1;
      padding: 14px;
      text-align: center;
      margin-bottom: 12px;
      transition: border-color 0.2s ease, background 0.2s ease;
    }

    #drop.active {
      border-color: var(--accent);
      background: #0f172a;
    }

    button {
      appearance: none;
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: #052e16;
      font-weight: 700;
      padding: 10px 16px;
      cursor: pointer;
    }

    button:hover { background: var(--accent-hover); }
    button:disabled { background: #475569; color: #cbd5e1; cursor: not-allowed; }

    .status {
      margin-top: 12px;
      color: var(--muted);
      min-height: 20px;
    }

    progress {
      width: 100%;
      height: 10px;
      margin-top: 10px;
      accent-color: var(--accent);
    }

    #dl {
      display: none;
      margin-top: 12px;
      color: #86efac;
      text-decoration: none;
      font-weight: 600;
    }

    #dl:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>MasterForge 320</h1>
    <div class="sub">AI Mastering + MP3 Enhancer</div>

    <div class="card">
      <label for="file">Input file</label>
      <input id="file" type="file" accept=".mp3,.wav,.flac"/>

      <div id="drop">Drop MP3 / WAV / FLAC here</div>

      <label for="mode">Mode</label>
      <select id="mode">
        <option value="music">music</option>
        <option value="speech">speech</option>
        <option value="aggressive">aggressive</option>
      </select>

      <div class="row">
        <button id="enhanceBtn" onclick="upload()">Enhance</button>
      </div>

      <progress id="progress" max="100" value="0"></progress>
      <div class="status" id="status">Ready</div>
      <a id="dl">Download enhanced file</a>
    </div>
  </div>

<script>
let dropped = null;
const drop = document.getElementById('drop');
const statusEl = document.getElementById('status');
const progressEl = document.getElementById('progress');
const enhanceBtn = document.getElementById('enhanceBtn');
const dlEl = document.getElementById('dl');

function setStatus(text){ statusEl.innerText = text; }

drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('active'); });
drop.addEventListener('dragleave', () => drop.classList.remove('active'));
drop.addEventListener('drop', e => {
  e.preventDefault();
  drop.classList.remove('active');
  dropped = e.dataTransfer.files[0];
  setStatus("Selected: " + dropped.name);
});

async function upload(){
  const f = dropped || document.getElementById('file').files[0];
  if(!f){ alert("Choose a file"); return; }
  dlEl.style.display = 'none';
  enhanceBtn.disabled = true;
  progressEl.value = 15;

  const fd = new FormData();
  fd.append('file', f);
  fd.append('mode', document.getElementById('mode').value);
  setStatus("Processing...");

  try {
    const r = await fetch('/enhance', { method:'POST', body: fd });
    progressEl.value = 85;

    if(!r.ok){
      let msg = 'Failed';
      try {
        const j = await r.json();
        msg = j.error || msg;
      } catch(_e) {}
      setStatus(msg);
      return;
    }

    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    dlEl.href = url;
    dlEl.download = "enhanced.mp3";
    dlEl.style.display = 'inline-block';
    dlEl.innerText = 'Download enhanced file';
    progressEl.value = 100;
    setStatus("Done");
  } catch (_err) {
    setStatus("Request failed");
  } finally {
    enhanceBtn.disabled = false;
  }
}
</script>
</body>
</html>
"""

@app.get("/")
def index():
    return render_template_string(HTML)


@app.post("/enhance")
def enhance_endpoint():
  f = request.files.get("file")
  mode = request.form.get("mode", "music")
  if not f:
    return jsonify({"error": "No file"}), 400

  file_name = f.filename or "input"
  ext = Path(file_name).suffix.lower()
  if ext not in SUPPORTED_EXTS:
    return jsonify({"error": "Supported formats: MP3, WAV, FLAC"}), 400

  if mode not in {"music", "speech", "aggressive"}:
    return jsonify({"error": "Invalid mode"}), 400

  with tempfile.TemporaryDirectory() as td:
    in_path = os.path.join(td, file_name)
    f.save(in_path)

    cfg = PipelineConfig(mode=mode)
    out_path = enhance_file(in_path, config=cfg)

    # ensure path exists and stream output
    if not Path(out_path).exists():
      return jsonify({"error": "Processing failed"}), 500

    return send_file(out_path, as_attachment=True, download_name="enhanced.mp3", mimetype="audio/mpeg")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)