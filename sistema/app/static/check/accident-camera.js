(function () {
  "use strict";

  const RecordingState = { stream: null, recorder: null, chunks: [], dialog: null };

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
    const blob = new Blob(RecordingState.chunks, { type: mime || "video/webm" });
    const fd = new FormData();
    fd.append("chave", chave);
    fd.append(
      "idempotency_key",
      crypto.randomUUID
        ? crypto.randomUUID()
        : Date.now().toString(36) + Math.random().toString(36).slice(2)
    );
    fd.append("video", blob, `recording.${mime.includes("mp4") ? "mp4" : "webm"}`);
    setStatus("Enviando vídeo…");
    try {
      const resp = await fetch("/api/web/check/accident/video", {
        method: "POST",
        body: fd,
        credentials: "include",
      });
      if (!resp.ok) throw new Error("upload failed");
      setStatus("Vídeo enviado.");
    } catch (err) {
      setStatus("Falha ao enviar vídeo: " + err.message);
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

    card.appendChild(video);
    card.appendChild(statusEl);
    card.appendChild(stopBtn);
    backdrop.appendChild(card);
    document.body.appendChild(backdrop);

    RecordingState.dialog = { backdrop, statusEl };
  }

  function setStatus(msg) {
    if (RecordingState.dialog) {
      RecordingState.dialog.statusEl.textContent = msg;
    }
  }

  function cleanup() {
    if (RecordingState.stream) {
      RecordingState.stream.getTracks().forEach((t) => t.stop());
    }
    RecordingState.stream = null;
    RecordingState.recorder = null;
    RecordingState.chunks = [];
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
