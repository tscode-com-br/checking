(function () {
  "use strict";

  const RecordingState = { stream: null, recorder: null, chunks: [], dialog: null, stopBtn: null };

  // i18n helper — uses window.CheckingWebI18n.t when available; otherwise
  // returns the pt-BR fallback text (which is the canonical wording required
  // by item 5.2 of docs/temp002_alteracoes.txt — do not change these strings
  // without explicit authorization).
  function tt(key, fallback) {
    const i18n = window.CheckingWebI18n;
    if (i18n && typeof i18n.t === "function") {
      try {
        const result = i18n.t(key);
        if (typeof result === "string" && result && result !== key) return result;
      } catch (_) {
        // fall through to fallback
      }
    }
    return fallback;
  }

  function getMimeType() {
    const candidates = ["video/webm;codecs=vp9,opus", "video/webm", "video/mp4"];
    for (const m of candidates) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(m)) return m;
    }
    return "";
  }

  async function startRecording(chave) {
    try {
      RecordingState.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: true,
      });
    } catch (err) {
      alert("Sem permissão para câmera/microfone. Habilite em Ajustes → Permitir Audio & Video.");
      return false;
    }
    showRecordingDialog();
    RecordingState.chunks = [];
    const mime = getMimeType();
    try {
      RecordingState.recorder = new MediaRecorder(
        RecordingState.stream,
        mime ? { mimeType: mime } : {}
      );
    } catch (err) {
      cleanup();
      alert("Seu dispositivo não suporta gravação de vídeo.");
      return false;
    }
    RecordingState.recorder.ondataavailable = (e) => {
      if (e.data && e.data.size) RecordingState.chunks.push(e.data);
    };
    RecordingState.recorder.onstop = () => uploadRecording(chave, mime);
    RecordingState.recorder.start();
    return true;
  }

  function stopRecording() {
    if (RecordingState.recorder && RecordingState.recorder.state !== "inactive") {
      RecordingState.recorder.stop();
    }
  }

  async function uploadRecording(chave, mime) {
    // Strip codec suffix (e.g. "video/webm;codecs=vp9,opus" → "video/webm")
    // so the server MIME-type check against ALLOWED_VIDEO_TYPES always passes.
    const baseMime = (mime || "video/webm").split(";")[0].trim() || "video/webm";
    const blob = new Blob(RecordingState.chunks, { type: baseMime });
    const fd = new FormData();
    fd.append("chave", chave);
    fd.append(
      "idempotency_key",
      crypto.randomUUID
        ? crypto.randomUUID()
        : Date.now().toString(36) + Math.random().toString(36).slice(2)
    );
    fd.append("video", blob, `recording.${baseMime.includes("mp4") ? "mp4" : "webm"}`);
    // Item 5.2 spec: these three texts are the user-visible contract for the
    // video upload feedback. Do not change them without explicit authorization.
    const sendingText = tt("accident.video.sending", "Enviando o registro...");
    const sentText = tt("accident.video.sent", "Registro enviado com sucesso.");
    const errorText = tt("accident.video.error", "Erro: registro não enviado.");
    setStatus(sendingText);
    setExternalStatus(sendingText);
    // Hide stop button and show progress bar while uploading.
    if (RecordingState.stopBtn) RecordingState.stopBtn.hidden = true;
    if (RecordingState.dialog && RecordingState.dialog.progressEl) {
      RecordingState.dialog.progressEl.hidden = false;
      RecordingState.dialog.progressEl.value = 0;
    }
    try {
      await new Promise(function (resolve, reject) {
        const xhr = new XMLHttpRequest();
        xhr.withCredentials = true;
        xhr.open("POST", "/api/web/check/accident/video");
        xhr.upload.onprogress = function (e) {
          if (!e.lengthComputable) return;
          const pct = Math.round((e.loaded / e.total) * 100);
          if (RecordingState.dialog && RecordingState.dialog.progressEl) {
            RecordingState.dialog.progressEl.value = pct;
          }
        };
        xhr.onload = function () {
          if (xhr.status >= 200 && xhr.status < 300) resolve();
          else reject(new Error("upload failed: " + xhr.status));
        };
        xhr.onerror = function () { reject(new Error("upload network error")); };
        xhr.send(fd);
      });
      setStatus(sentText);
      setExternalStatus(sentText);
    } catch (err) {
      setStatus(errorText);
      setExternalStatus(errorText);
    } finally {
      cleanup();
    }
  }

  function showRecordingDialog() {
    if (RecordingState.dialog) return;

    const backdrop = document.createElement("div");
    backdrop.className = "accident-camera-backdrop";

    const card = document.createElement("div");
    card.className = "accident-camera-card";

    const video = document.createElement("video");
    video.className = "accident-camera-preview";
    video.autoplay = true;
    video.muted = true;
    video.playsInline = true;
    video.srcObject = RecordingState.stream;

    const statusEl = document.createElement("p");
    statusEl.className = "accident-camera-status";
    statusEl.textContent = "Gravando…";

    const stopBtn = document.createElement("button");
    stopBtn.type = "button";
    stopBtn.className = "accident-camera-stop-button";
    stopBtn.textContent = "Encerrar";
    stopBtn.addEventListener("click", stopRecording);

    const progressEl = document.createElement("progress");
    progressEl.className = "accident-camera-progress";
    progressEl.max = 100;
    progressEl.value = 0;
    progressEl.hidden = true;

    card.appendChild(video);
    card.appendChild(statusEl);
    card.appendChild(progressEl);
    card.appendChild(stopBtn);
    backdrop.appendChild(card);
    document.body.appendChild(backdrop);

    RecordingState.dialog = { backdrop, statusEl, progressEl };
    RecordingState.stopBtn = stopBtn;
  }

  function setStatus(msg) {
    if (RecordingState.dialog) {
      RecordingState.dialog.statusEl.textContent = msg;
    }
  }

  function setExternalStatus(msg) {
    const el = document.getElementById("notificationLineSecondary");
    if (el) el.textContent = msg;
  }

  function cleanup() {
    if (RecordingState.stream) {
      RecordingState.stream.getTracks().forEach((t) => t.stop());
    }
    RecordingState.stream = null;
    RecordingState.recorder = null;
    RecordingState.chunks = [];
    RecordingState.stopBtn = null;
    hideRecordingDialog();
  }

  function hideRecordingDialog() {
    if (RecordingState.dialog) {
      RecordingState.dialog.backdrop.remove();
      RecordingState.dialog = null;
    }
  }

  window.AccidentCamera = { startRecording, stopRecording };
})();
