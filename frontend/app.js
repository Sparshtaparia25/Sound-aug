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
    
    document.getElementById('prompt-input').addEventListener('input', checkAnalyzeReadiness);
    
    // Initial State
    updateWorkflowState("NO_REQUEST");
});

function updateWorkflowState(stateStr) {
    document.getElementById('global-state').innerText = stateStr.replace(/_/g, ' ');
    const dot = document.getElementById('global-status-dot');
    dot.className = 'status-dot'; // reset
    
    const wfSource = document.getElementById('wf-source');
    const wfTransform = document.getElementById('wf-transform');
    const wfPlan = document.getElementById('wf-plan');
    const wfGenerate = document.getElementById('wf-generate');
    const wfResults = document.getElementById('wf-results');
    
    const line1 = document.getElementById('wf-line-1');
    const line2 = document.getElementById('wf-line-2');
    const line3 = document.getElementById('wf-line-3');
    const line4 = document.getElementById('wf-line-4');

    if (stateStr === "NO_REQUEST") {
        dot.classList.add('active'); // just active/idle
    } 
    else if (stateStr === "FILES_READY") {
        dot.classList.add('active');
        document.getElementById('source-status').classList.remove('hidden');
        wfSource.className = 'step-node completed';
        line1.classList.add('active');
        wfTransform.className = 'step-node active';
        
        document.getElementById('stage-02').classList.remove('hidden');
    }
    else if (stateStr === "PROFILING_AND_PLANNING") {
        dot.classList.add('active');
        wfTransform.className = 'step-node active';
    }
    else if (stateStr === "PLAN_READY") {
        dot.classList.add('active');
        document.getElementById('transform-status').classList.remove('hidden');
        wfTransform.className = 'step-node completed';
        line2.classList.add('active');
        wfPlan.className = 'step-node completed'; // plan is immediately shown and ready for approval
        line3.classList.add('active');
        wfGenerate.className = 'step-node active';
        
        document.getElementById('stage-03').classList.remove('hidden');
        document.getElementById('stage-04').classList.remove('hidden');
    }
    else if (stateStr === "AUGMENTING" || stateStr === "PROFILING_OUTPUT" || stateStr === "QUALITY_CHECK") {
        dot.classList.add('active');
        wfGenerate.className = 'step-node active';
        document.getElementById('stage-05').classList.remove('hidden');
    }
    else if (stateStr === "COMPLETED") {
        dot.classList.add('success');
        wfGenerate.className = 'step-node completed';
        line4.classList.add('active');
        wfResults.className = 'step-node completed';
        
        document.getElementById('qa-status-badge').classList.remove('hidden');
        document.getElementById('stage-06').classList.remove('hidden');
    }
    else if (stateStr.includes("FAILED") || stateStr.includes("ERROR")) {
        dot.classList.add('error');
    }
}

function checkAnalyzeReadiness() {
    const prompt = document.getElementById('prompt-input').value.trim();
    const btn = document.getElementById('analyze-btn');
    if (uploadedFiles.length > 0 && prompt.length > 0) {
        btn.disabled = false;
        btn.innerText = "✨ ANALYZE & CREATE PLAN";
    } else {
        btn.disabled = true;
        btn.innerText = "ANALYZE & CREATE PLAN";
    }
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
    
    // Shrink the drop zone and show the side-by-side grid
    document.getElementById('drop-zone').classList.add('compact');
    document.getElementById('source-content').classList.remove('hidden');
    
    const list = document.getElementById('file-list');
    list.innerHTML = '';
    
    uploadedFiles.forEach(file => {
        const li = document.createElement('li');
        li.innerHTML = `
            <div class="file-info">
                <span class="name">🎵 ${file.name}</span>
                <span class="meta">${(file.size / 1024 / 1024).toFixed(2)} MB</span>
            </div>
            <div class="file-status">✓ Ready</div>
        `;
        list.appendChild(li);
    });
    
    document.getElementById('file-count-text').innerText = `SOURCE AUDIO — ${uploadedFiles.length} FILE${uploadedFiles.length > 1 ? 'S' : ''}`;
    document.getElementById('preview-filename').innerText = uploadedFiles[0].name;
    
    // Load first file into original waveform
    const fileUrl = URL.createObjectURL(uploadedFiles[0]);
    originalWaveSurfer.load(fileUrl);
    
    updateWorkflowState("FILES_READY");
    checkAnalyzeReadiness();
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
            checkAnalyzeReadiness();
        });
    });
}

async function handleAnalyze() {
    const prompt = document.getElementById('prompt-input').value.trim();
    if (!prompt || uploadedFiles.length === 0) return;
    
    updateWorkflowState("PROFILING_AND_PLANNING");
    const btn = document.getElementById('analyze-btn');
    btn.disabled = true;
    btn.innerText = "ANALYZING...";
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
        
        if (!response.ok || data.status === "PLAN_FAILED") {
            throw new Error(data.message || "Failed to analyze.");
        }
        
        if (data.status === "NEEDS_CLARIFICATION") {
            updateWorkflowState("NEEDS_CLARIFICATION");
            btn.disabled = false;
            btn.innerText = "✨ ANALYZE & CREATE PLAN";
            
            const box = document.getElementById('clarification-box');
            box.classList.remove('hidden');
            document.getElementById('clarification-reason').innerText = data.message;
            
            const optionsDiv = document.getElementById('clarification-options');
            optionsDiv.innerHTML = '';
            data.suggested_options.forEach(opt => {
                const optBtn = document.createElement('button');
                optBtn.className = 'chip';
                optBtn.innerText = opt;
                optBtn.onclick = () => { 
                    document.getElementById('prompt-input').value = opt; 
                    box.classList.add('hidden'); 
                    checkAnalyzeReadiness();
                };
                optionsDiv.appendChild(optBtn);
            });
            return;
        }
        
        if (data.status === "PLAN_READY") {
            currentRequestId = data.request_id;
            
            // Populate Stage 3
            document.getElementById('kpi-duration').innerText = `${data.input_profile.file_info.duration.toFixed(1)}s`;
            document.getElementById('kpi-sr').innerText = `${(data.input_profile.file_info.sample_rate/1000).toFixed(1)} kHz`;
            document.getElementById('kpi-ch').innerText = data.input_profile.file_info.channels === 1 ? 'Mono' : 'Stereo';
            document.getElementById('kpi-snr').innerText = `${data.input_profile.noise.estimated_snr.toFixed(1)} dB`;
            document.getElementById('kpi-rms').innerText = `${data.input_profile.signal_quality.rms.toFixed(2)} dB`;
            document.getElementById('kpi-peak').innerText = `${data.input_profile.signal_quality.peak.toFixed(2)} dB`;
            document.getElementById('full-profile-json').innerText = JSON.stringify(data.input_profile, null, 2);
            
            // Populate Stage 4
            document.getElementById('intent-json').innerText = JSON.stringify(data.intent, null, 2);
            const opList = document.getElementById('operations-list');
            opList.innerHTML = '';
            data.plan.operations.forEach(op => {
                const li = document.createElement('li');
                li.innerText = `✓ ${op.operation} ${op.profile ? `(${op.profile})` : ''}`;
                opList.appendChild(li);
            });
            
            btn.disabled = true;
            btn.innerText = "✓ PLAN CREATED";
            
            updateWorkflowState("PLAN_READY");
        }
        
    } catch (err) {
        console.error(err);
        updateWorkflowState("PLAN_FAILED");
        alert("Failed to analyze: " + err.message);
        btn.disabled = false;
        btn.innerText = "✨ ANALYZE & CREATE PLAN";
    }
}

async function handleApprove() {
    if (!currentRequestId) return;
    
    const approveBtn = document.getElementById('approve-btn');
    approveBtn.disabled = true;
    approveBtn.innerText = "GENERATING...";
    
    updateWorkflowState("AUGMENTING");
    
    try {
        const response = await fetch(`${API_BASE}/execute/${currentRequestId}`, { method: "POST" });
        const data = await response.json();
        
        if (data.status === "QUEUED" || data.status === "ACCEPTED") {
            pollJobStatus(currentRequestId);
        }
    } catch (err) {
        console.error(err);
        updateWorkflowState("EXECUTION_ERROR");
        approveBtn.disabled = false;
        approveBtn.innerText = "APPROVE & GENERATE";
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
            updateWorkflowState(data.status);
            
            // Rebuild progress list
            const states = ["RECEIVED", "PROFILING", "UNDERSTANDING_INTENT", "PLANNING", "PLAN_READY", "AUGMENTING", "PROFILING_OUTPUT", "QUALITY_CHECK", "COMPLETED"];
            const currentIndex = states.indexOf(data.status);
            
            list.innerHTML = '';
            states.forEach((s, idx) => {
                if (idx >= states.indexOf("AUGMENTING")) { // Only show execution steps here
                    const li = document.createElement('li');
                    li.innerText = s.replace(/_/g, ' ');
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
                alert("Processing failed: " + data.error_code);
            }
            
        } catch (err) {
            console.error(err);
        }
    }, 1000);
}

function populateResults(metadata) {
    // WaveSurfers for Results
    const fileOutput = metadata.files[0];
    
    document.getElementById('res-orig-file').innerText = fileOutput.original_filename;
    document.getElementById('res-aug-file').innerText = fileOutput.augmented_filename;
    
    if (!resOrigWaveSurfer) {
        resOrigWaveSurfer = WaveSurfer.create({ container: '#res-orig-waveform', waveColor: '#9CA3AF', progressColor: '#6366F1', height: 60, normalize: true });
        resAugWaveSurfer = WaveSurfer.create({ container: '#res-aug-waveform', waveColor: '#10B981', progressColor: '#3B82F6', height: 60, normalize: true });
        
        document.getElementById('play-res-orig').onclick = () => resOrigWaveSurfer.playPause();
        document.getElementById('play-res-aug').onclick = () => resAugWaveSurfer.playPause();
    }
    
    // Load audio using correct artifact URIs
    const baseUrl = "http://localhost:8000";
    resOrigWaveSurfer.load(baseUrl + fileOutput.original_uri);
    resAugWaveSurfer.load(baseUrl + fileOutput.augmented_uri);
    
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
        <tr>
            <td>Peak</td>
            <td class="text-right">${metadata.input_profile.signal_quality.peak.toFixed(2)} dB</td>
            <td class="text-right">${metadata.output_profile.signal_quality.peak.toFixed(2)} dB</td>
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
    
    if (metadata.quality.status === "WARN") {
        document.getElementById('qa-status-badge').innerText = "⚠ QA WARNING";
        document.getElementById('qa-status-badge').style.color = "var(--warning)";
    }
    
    document.getElementById('metadata-json').innerText = JSON.stringify(metadata, null, 2);
}
