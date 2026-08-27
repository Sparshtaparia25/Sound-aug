let uploadedFiles = [];
let currentRequestId = null;
let originalWaveSurfer = null;
let resOrigWaveSurfer = null;
let resAugWaveSurfer = null;

const API_BASE = "http://localhost:8000/api";

document.addEventListener('DOMContentLoaded', () => {
    setupDragAndDrop();
    setupPromptChips();
    setupWaveSurfers();
    
    document.getElementById('analyze-btn').addEventListener('click', handleAnalyze);
    document.getElementById('approve-btn').addEventListener('click', handleApprove);
});

function setState(stateStr) {
    document.getElementById('global-state').innerText = stateStr;
}

function showStage(stageNum) {
    document.getElementById(`stage-0${stageNum}`).classList.remove('hidden');
}

function setupWaveSurfers() {
    originalWaveSurfer = WaveSurfer.create({
        container: '#original-waveform',
        waveColor: '#4F46E5',
        progressColor: '#3B82F6',
        height: 60,
        normalize: true,
    });
    
    document.getElementById('play-original-btn').addEventListener('click', () => {
        originalWaveSurfer.playPause();
    });
}

function setupDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#3B82F6';
    });
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#374151';
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#374151';
        handleFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
}

function handleFiles(files) {
    if (files.length === 0) return;
    
    uploadedFiles = Array.from(files);
    
    document.getElementById('drop-zone').classList.add('hidden');
    document.getElementById('file-list-container').classList.remove('hidden');
    
    const list = document.getElementById('file-list');
    list.innerHTML = '';
    
    uploadedFiles.forEach(file => {
        const li = document.createElement('li');
        li.innerHTML = `
            <div class="file-info">
                <span>🎵 ${file.name}</span>
                <span>${(file.size / 1024 / 1024).toFixed(2)} MB</span>
            </div>
            <div class="file-status">✓ Ready</div>
        `;
        list.appendChild(li);
    });
    
    document.getElementById('file-count').innerText = uploadedFiles.length;
    
    // Load first file into original waveform
    const fileUrl = URL.createObjectURL(uploadedFiles[0]);
    document.getElementById('original-waveform-container').classList.remove('hidden');
    originalWaveSurfer.load(fileUrl);
    
    setState("FILES_SELECTED");
    showStage(2); // Reveal Transformation stage
}

function setupPromptChips() {
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', (e) => {
            const prompt = e.target.getAttribute('data-prompt');
            const textarea = document.getElementById('prompt-input');
            if (textarea.value) {
                textarea.value += ' ' + prompt;
            } else {
                textarea.value = prompt;
            }
        });
    });
}

async function handleAnalyze() {
    const prompt = document.getElementById('prompt-input').value;
    if (!prompt || uploadedFiles.length === 0) return;
    
    setState("PROFILING_AND_PLANNING");
    document.getElementById('analyze-btn').disabled = true;
    document.getElementById('analyze-btn').innerText = "ANALYZING...";
    document.getElementById('clarification-box').classList.add('hidden');
    
    const formData = new FormData();
    formData.append("prompt", prompt);
    uploadedFiles.forEach(f => formData.append("files", f));
    
    try {
        const response = await fetch(`${API_BASE}/plan`, {
            method: "POST",
            body: formData
        });
        
        const data = await response.json();
        
        if (data.status === "NEEDS_CLARIFICATION") {
            setState("NEEDS_CLARIFICATION");
            document.getElementById('analyze-btn').disabled = false;
            document.getElementById('analyze-btn').innerText = "ANALYZE & CREATE PLAN";
            
            const box = document.getElementById('clarification-box');
            box.classList.remove('hidden');
            document.getElementById('clarification-reason').innerText = data.message;
            
            const optionsDiv = document.getElementById('clarification-options');
            optionsDiv.innerHTML = '';
            data.suggested_options.forEach(opt => {
                const btn = document.createElement('button');
                btn.className = 'chip';
                btn.innerText = opt;
                btn.onclick = () => { document.getElementById('prompt-input').value = opt; box.classList.add('hidden'); };
                optionsDiv.appendChild(btn);
            });
            return;
        }
        
        if (data.status === "PLAN_READY") {
            currentRequestId = data.request_id;
            setState("PLAN_READY");
            
            // Populate Stage 3
            document.getElementById('kpi-duration').innerText = `${data.input_profile.file_info.duration.toFixed(1)}s`;
            document.getElementById('kpi-sr').innerText = `${(data.input_profile.file_info.sample_rate/1000).toFixed(1)} kHz`;
            document.getElementById('kpi-ch').innerText = data.input_profile.file_info.channels === 1 ? 'Mono' : 'Stereo';
            document.getElementById('kpi-snr').innerText = `${data.input_profile.noise.estimated_snr.toFixed(1)} dB`;
            document.getElementById('kpi-rms').innerText = `${data.input_profile.signal_quality.rms.toFixed(2)} dB`;
            document.getElementById('kpi-peak').innerText = `${data.input_profile.signal_quality.peak.toFixed(2)} dB`;
            document.getElementById('full-profile-json').innerText = JSON.stringify(data.input_profile, null, 2);
            
            showStage(3);
            
            // Populate Stage 4
            document.getElementById('intent-json').innerText = JSON.stringify(data.intent, null, 2);
            const opList = document.getElementById('operations-list');
            opList.innerHTML = '';
            data.plan.operations.forEach(op => {
                const li = document.createElement('li');
                li.innerText = `✓ ${op.operation} ${op.profile ? `(${op.profile})` : ''}`;
                opList.appendChild(li);
            });
            
            showStage(4);
            
            document.getElementById('analyze-btn').disabled = false;
            document.getElementById('analyze-btn').innerText = "ANALYZE & CREATE PLAN";
        }
        
    } catch (err) {
        console.error(err);
        setState("ERROR");
        alert("Failed to analyze. Check console.");
        document.getElementById('analyze-btn').disabled = false;
        document.getElementById('analyze-btn').innerText = "ANALYZE & CREATE PLAN";
    }
}

async function handleApprove() {
    if (!currentRequestId) return;
    
    setState("AUGMENTING");
    document.getElementById('approve-btn').disabled = true;
    showStage(5); // Progress
    
    try {
        const response = await fetch(`${API_BASE}/execute/${currentRequestId}`, { method: "POST" });
        const data = await response.json();
        
        if (data.status === "ACCEPTED") {
            pollJobStatus(currentRequestId);
        }
    } catch (err) {
        console.error(err);
        setState("ERROR");
    }
}

async function pollJobStatus(reqId) {
    const list = document.getElementById('progress-list');
    const bar = document.getElementById('job-progress-bar');
    
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/jobs/${reqId}`);
            const data = await res.json();
            
            bar.style.width = `${data.progress}%`;
            setState(data.status);
            
            // Rebuild progress list
            const states = ["RECEIVED", "PROFILING", "UNDERSTANDING_INTENT", "PLANNING", "PLAN_READY", "AUGMENTING", "PROFILING_OUTPUT", "QUALITY_CHECK", "COMPLETED"];
            const currentIndex = states.indexOf(data.status);
            
            list.innerHTML = '';
            states.forEach((s, idx) => {
                if (idx > states.indexOf("PLAN_READY")) { // Only show execution steps here
                    const li = document.createElement('li');
                    li.innerText = s;
                    if (idx < currentIndex) li.className = 'done';
                    else if (idx === currentIndex) li.className = 'active';
                    else li.className = 'pending';
                    list.appendChild(li);
                }
            });
            
            if (data.status === "COMPLETED") {
                clearInterval(interval);
                populateResults(data.metadata);
            } else if (data.status === "PROCESSING_FAILED") {
                clearInterval(interval);
                alert("Processing failed: " + data.error);
            }
            
        } catch (err) {
            console.error(err);
        }
    }, 1000);
}

function populateResults(metadata) {
    showStage(6);
    
    // WaveSurfers for Results
    const fileOutput = metadata.files[0];
    
    document.getElementById('res-orig-file').innerText = fileOutput.filename;
    document.getElementById('res-aug-file').innerText = "aug_" + fileOutput.filename;
    
    if (!resOrigWaveSurfer) {
        resOrigWaveSurfer = WaveSurfer.create({ container: '#res-orig-waveform', waveColor: '#9CA3AF', progressColor: '#6366F1', height: 60, normalize: true });
        resAugWaveSurfer = WaveSurfer.create({ container: '#res-aug-waveform', waveColor: '#10B981', progressColor: '#3B82F6', height: 60, normalize: true });
        
        document.getElementById('play-res-orig').onclick = () => resOrigWaveSurfer.playPause();
        document.getElementById('play-res-aug').onclick = () => resAugWaveSurfer.playPause();
    }
    
    // Load audio
    // Assuming backend is hosted at API_BASE, we need absolute urls for audio
    const baseUrl = "http://localhost:8000";
    resOrigWaveSurfer.load(baseUrl + fileOutput.original);
    resAugWaveSurfer.load(baseUrl + fileOutput.augmented);
    
    // Metrics
    const tbody = document.getElementById('metrics-tbody');
    tbody.innerHTML = `
        <tr>
            <td>SNR</td>
            <td class="text-right">${metadata.input_profile.noise.estimated_snr.toFixed(1)} dB</td>
            <td class="text-right">${metadata.output_profile.noise.estimated_snr.toFixed(1)} dB</td>
            <td>✓</td>
        </tr>
        <tr>
            <td>RMS</td>
            <td class="text-right">${metadata.input_profile.signal_quality.rms.toFixed(2)} dB</td>
            <td class="text-right">${metadata.output_profile.signal_quality.rms.toFixed(2)} dB</td>
            <td>✓</td>
        </tr>
    `;
    
    // QA checks
    const qaList = document.getElementById('qa-checklist');
    qaList.innerHTML = '';
    metadata.quality.checks.forEach(c => {
        const li = document.createElement('li');
        li.innerText = c;
        li.className = c.includes("WARN") ? "warn" : "pass";
        qaList.appendChild(li);
    });
    
    document.getElementById('metadata-json').innerText = JSON.stringify(metadata, null, 2);
}
