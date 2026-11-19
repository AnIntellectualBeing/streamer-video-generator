(() => {
  const form = document.querySelector('#studio-form');
  const faceInput = document.querySelector('#facecam');
  const gameInput = document.querySelector('#gameplay');
  const faceVideo = document.querySelector('#facecam-player');
  const gameVideo = document.querySelector('#gameplay-player');
  const canvas = document.querySelector('#composite');
  const context = canvas.getContext('2d');
  const empty = document.querySelector('#empty-preview');
  const faceRatio = document.querySelector('#facecam_height');
  const subtitleText = document.querySelector('#subtitle_text');
  const jobPanel = document.querySelector('#job-panel');
  const generate = document.querySelector('#generate');
  let faceUrl = null;
  let gameUrl = null;
  let pollTimer = null;

  const values = {
    faceFocusX: document.querySelector('#facecam_focus_x'),
    faceFocusY: document.querySelector('#facecam_focus_y'),
    gameFocusX: document.querySelector('#gameplay_focus_x'),
    gameFocusY: document.querySelector('#gameplay_focus_y'),
  };

  function cover(video, x, y, width, height, focusX, focusY) {
    if (!video.videoWidth || !video.videoHeight) return;
    const sourceRatio = video.videoWidth / video.videoHeight;
    const targetRatio = width / height;
    let sw = video.videoWidth;
    let sh = video.videoHeight;
    if (sourceRatio > targetRatio) sw = sh * targetRatio;
    else sh = sw / targetRatio;
    const sx = (video.videoWidth - sw) * focusX;
    const sy = (video.videoHeight - sh) * focusY;
    context.drawImage(video, sx, sy, sw, sh, x, y, width, height);
  }

  function drawPreview() {
    const split = canvas.height * Number(faceRatio.value) / 1920;
    context.fillStyle = '#08090c';
    context.fillRect(0, 0, canvas.width, canvas.height);
    cover(faceVideo, 0, 0, canvas.width, split, values.faceFocusX.value / 100, values.faceFocusY.value / 100);
    cover(gameVideo, 0, split, canvas.width, canvas.height - split, values.gameFocusX.value / 100, values.gameFocusY.value / 100);
    context.fillStyle = 'rgba(3, 5, 8, .65)';
    context.fillRect(24, canvas.height - 138, canvas.width - 48, 80);
    context.font = '800 27px Arial';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.lineWidth = 4;
    context.strokeStyle = '#101010';
    context.fillStyle = '#fff';
    const firstLine = subtitleText.value.split('\n').find((line) => line.trim() && !line.includes('-->') && !/^\d+$/.test(line.trim()));
    if (firstLine) {
      const caption = firstLine.trim().slice(0, 34);
      context.strokeText(caption, canvas.width / 2, canvas.height - 97, canvas.width - 55);
      context.fillText(caption, canvas.width / 2, canvas.height - 97, canvas.width - 55);
    }
    empty.hidden = Boolean(faceVideo.videoWidth && gameVideo.videoWidth);
    requestAnimationFrame(drawPreview);
  }

  function loadVideo(input, player, side) {
    const file = input.files?.[0];
    if (!file) return;
    const old = side === 'face' ? faceUrl : gameUrl;
    if (old) URL.revokeObjectURL(old);
    const url = URL.createObjectURL(file);
    if (side === 'face') faceUrl = url;
    else gameUrl = url;
    player.src = url;
    player.play().catch(() => {});
    document.querySelector(`#${side === 'face' ? 'facecam' : 'gameplay'}-name`).textContent = file.name;
  }

  faceInput.addEventListener('change', () => loadVideo(faceInput, faceVideo, 'face'));
  gameInput.addEventListener('change', () => loadVideo(gameInput, gameVideo, 'game'));
  for (const slider of Object.values(values)) slider.addEventListener('input', () => {
    document.querySelector('#face-focus-value').textContent = `${values.faceFocusX.value} / ${values.faceFocusY.value}`;
    document.querySelector('#game-focus-value').textContent = `${values.gameFocusX.value} / ${values.gameFocusY.value}`;
  });
  faceRatio.addEventListener('input', () => { document.querySelector('#split-value').textContent = `${Math.round(faceRatio.value / 19.2)}% top`; });
  for (const [inputId, outputId] of [['streamer_volume', 'streamer-volume-value'], ['gameplay_volume', 'gameplay-volume-value']]) {
    document.querySelector(`#${inputId}`).addEventListener('input', (event) => { document.querySelector(`#${outputId}`).textContent = `${event.target.value}%`; });
  }
  document.querySelector('#subtitle-file').addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    subtitleText.value = await file.text();
    document.querySelector('#subtitle-name').textContent = file.name;
  });

  async function pollJob(jobId) {
    try {
      const response = await fetch(`/api/jobs/${jobId}`);
      const job = await response.json();
      if (!response.ok) throw new Error(job.detail || 'Could not read render status.');
      document.querySelector('#job-title').textContent = job.status === 'done' ? 'Your short is ready' : job.status === 'error' ? 'Render needs attention' : 'Rendering your short';
      document.querySelector('#job-percent').textContent = `${Math.round(job.progress * 100)}%`;
      document.querySelector('#progress-fill').style.width = `${Math.round(job.progress * 100)}%`;
      document.querySelector('#job-message').textContent = job.message;
      if (job.status === 'done') {
        const result = document.querySelector('#result-player');
        result.src = job.download_url;
        result.hidden = false;
        document.querySelector('#download-link').href = job.download_url;
        document.querySelector('#download-link').hidden = false;
        generate.disabled = false;
      } else if (job.status === 'error') {
        generate.disabled = false;
      } else {
        pollTimer = window.setTimeout(() => pollJob(jobId), 1100);
      }
    } catch (error) {
      document.querySelector('#job-message').textContent = error.message;
      generate.disabled = false;
    }
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!faceInput.files.length || !gameInput.files.length) {
      alert('Add both the streamer video and the gameplay footage first.');
      return;
    }
    if (pollTimer) clearTimeout(pollTimer);
    jobPanel.hidden = false;
    document.querySelector('#result-player').hidden = true;
    document.querySelector('#download-link').hidden = true;
    document.querySelector('#job-title').textContent = 'Uploading source videos';
    document.querySelector('#job-message').textContent = 'Uploads stay on this computer.';
    document.querySelector('#progress-fill').style.width = '0%';
    generate.disabled = true;
    jobPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });

    const data = new FormData(form);
    const request = new XMLHttpRequest();
    request.open('POST', '/api/jobs');
    request.upload.addEventListener('progress', (uploadEvent) => {
      if (!uploadEvent.lengthComputable) return;
      const progress = Math.min(15, uploadEvent.loaded / uploadEvent.total * 15);
      document.querySelector('#job-percent').textContent = `${Math.round(progress)}%`;
      document.querySelector('#progress-fill').style.width = `${progress}%`;
    });
    request.addEventListener('load', () => {
      const response = JSON.parse(request.responseText || '{}');
      if (request.status < 200 || request.status >= 300) {
        document.querySelector('#job-title').textContent = 'Upload could not start';
        document.querySelector('#job-message').textContent = response.detail || 'Check your files and try again.';
        generate.disabled = false;
        return;
      }
      pollJob(response.id);
    });
    request.addEventListener('error', () => {
      document.querySelector('#job-title').textContent = 'Connection interrupted';
      document.querySelector('#job-message').textContent = 'Keep the local studio running and try the upload again.';
      generate.disabled = false;
    });
    request.send(data);
  });

  drawPreview();
})();
