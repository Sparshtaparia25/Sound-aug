let uploadedFiles = [];
let currentRequestId = null;
let originalWaveSurfer = null;
let resOrigWaveSurfer = null;
let resAugWaveSurfer = null;

const API_BASE = "http://localhost:8000/api";

let toastTimeout;
function showToast(title, message, type = "error") {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toast-title');
    const toastMessage = document.getElementById('toast-message');
    const toastIcon = document.getElementById('toast-icon');

    toastTitle.innerText = title;
    toastMessage.innerText = message;
    
    if (type === "error") {
        toast.className = "toast error show";
        toastIcon.innerText = "⚠️";
    } else if (type === "success") {
        toast.className = "toast show";
        toastIcon.innerText = "✓";
        toast.style.borderLeftColor = "var(--success)";
        toastIcon.style.color = "var(--success)";
    }

    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
        hideToast();
    }, 5000);
}

function hideToast() {
    const toast = document.getElementById('toast');
    toast.className = "toast";
}

document.addEventListener('DOMContentLoaded', () => {
    setupDragAndDrop();
    setupPromptChips();
    setupWaveSurfers();
    
    document.getElementById('analyze-btn').addEventListener('click', handleAnalyze);
    document.getElementById('approve-btn').addEventListener('click', handleApprove);
    
    document.getElementById('proceed-btn').addEventListener('click', () => {
        updateWorkflowState("PROMPT_READY");
    });

    document.getElementById('back-to-01-btn').addEventListener('click', () => {
        updateWorkflowState("FILES_READY");
    });
    
    document.getElementById('start-new-btn').addEventListener('click', () => {
        uploadedFiles = [];
        currentRequestId = null;
        document.getElementById('file-list').innerHTML = '';
        document.getElementById('source-content').classList.add('hidden');
        document.getElementById('drop-zone').classList.remove('compact');
        document.getElementById('prompt-input').value = '';
        updateWorkflowState("NO_REQUEST");
    });

    document.getElementById('edit-prompt-btn').addEventListener('click', () => {
        document.getElementById('stage-03').classList.add('hidden');
        document.getElementById('stage-04').classList.add('hidden');
        updateWorkflowState("PROMPT_READY");
        
        const btn = document.getElementById('analyze-btn');
        btn.disabled = false;
        btn.innerText = "✨ RE-ANALYZE";
        document.getElementById('wf-plan').className = 'step-node pending';
        document.getElementById('wf-line-2').classList.remove('active');
        document.getElementById('wf-line-3').classList.remove('active');
    });
    
    document.getElementById('prompt-input').addEventListener('input', checkAnalyzeReadiness);
    
    // Initial State
    updateWorkflowState("NO_REQUEST");
});

function stopAllAudio() {
    if (originalWaveSurfer && originalWaveSurfer.isPlaying()) originalWaveSurfer.pause();
    if (resOrigWaveSurfer && resOrigWaveSurfer.isPlaying()) resOrigWaveSurfer.pause();
    if (resAugWaveSurfer && resAugWaveSurfer.isPlaying()) resAugWaveSurfer.pause();
}

function updateWorkflowState(stateStr) {
    stopAllAudio();
    
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
        document.getElementById('stage-01').classList.remove('hidden');
        document.getElementById('stage-02').classList.add('hidden');
        document.getElementById('stage-03').classList.add('hidden');
        document.getElementById('stage-04').classList.add('hidden');
        document.getElementById('stage-05').classList.add('hidden');
        document.getElementById('stage-06').classList.add('hidden');
        document.getElementById('stage-01').scrollIntoView({ behavior: 'smooth' });
        
        wfSource.className = 'step-node active';
        line1.classList.remove('active');
        wfTransform.className = 'step-node pending';
        line2.classList.remove('active');
        wfPlan.className = 'step-node pending';
        line3.classList.remove('active');
        wfGenerate.className = 'step-node pending';
        line4.classList.remove('active');
        wfResults.className = 'step-node pending';
    } 
    else if (stateStr === "FILES_READY") {
        dot.classList.add('active');
        document.getElementById('source-status').classList.remove('hidden');
        wfSource.className = 'step-node completed';
        line1.classList.add('active');
        document.getElementById('proceed-btn').classList.remove('hidden');
        
        document.getElementById('stage-01').classList.remove('hidden');
        document.getElementById('stage-02').classList.add('hidden');
        document.getElementById('stage-03').classList.add('hidden');
        document.getElementById('stage-04').classList.add('hidden');
        document.getElementById('stage-05').classList.add('hidden');
        document.getElementById('stage-06').classList.add('hidden');
        document.getElementById('stage-01').scrollIntoView({ behavior: 'smooth' });
        
        wfTransform.className = 'step-node pending'; // undo active state if going back
    }
    else if (stateStr === "PROMPT_READY") {
        wfTransform.className = 'step-node active';
        document.getElementById('stage-01').classList.add('hidden');
        document.getElementById('stage-02').classList.remove('hidden');
        document.getElementById('stage-02').scrollIntoView({ behavior: 'smooth' });
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
        
        document.getElementById('stage-01').classList.add('hidden');
        document.getElementById('stage-02').classList.add('hidden');
        document.getElementById('stage-03').classList.remove('hidden');
        document.getElementById('stage-04').classList.remove('hidden');
        document.getElementById('stage-03').scrollIntoView({ behavior: 'smooth' });
    }
    else if (stateStr === "AUGMENTING" || stateStr === "PROFILING_OUTPUT" || stateStr === "QUALITY_CHECK") {
        dot.classList.add('active');
        wfGenerate.className = 'step-node active';
        
        document.getElementById('stage-03').classList.add('hidden');
        document.getElementById('stage-04').classList.add('hidden');
        document.getElementById('stage-05').classList.remove('hidden');
        document.getElementById('stage-05').scrollIntoView({ behavior: 'smooth' });
    }
    else if (stateStr === "COMPLETED") {
        dot.classList.add('success');
        wfGenerate.className = 'step-node completed';
        line4.classList.add('active');
        wfResults.className = 'step-node completed';
        
        document.getElementById('stage-05').classList.add('hidden');
        document.getElementById('qa-status-badge').classList.remove('hidden');
        document.getElementById('stage-06').classList.remove('hidden');
        document.getElementById('stage-06').scrollIntoView({ behavior: 'smooth' });
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
    
    originalWaveSurfer.on('play', () => document.getElementById('play-original-btn').innerText = '⏸ Pause');
    originalWaveSurfer.on('pause', () => document.getElementById('play-original-btn').innerText = '▶ Play');
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
    
    const newFiles = Array.from(files);
    uploadedFiles = uploadedFiles.concat(newFiles);
    
    // Shrink the drop zone and show the side-by-side grid
    document.getElementById('drop-zone').classList.add('compact');
    document.getElementById('source-content').classList.remove('hidden');
    
    renderFileList();
    
    // Load first file into original waveform
    if (uploadedFiles.length > 0) {
        loadPreview(uploadedFiles[0]);
    }
    
    updateWorkflowState("FILES_READY");
    checkAnalyzeReadiness();
}

function renderFileList() {
    const list = document.getElementById('file-list');
    list.innerHTML = '';
    
    uploadedFiles.forEach((file, index) => {
        const li = document.createElement('li');
        li.innerHTML = `
            <div class="file-info">
                <span class="name">🎵 ${file.name}</span>
                <span class="meta">${(file.size / 1024 / 1024).toFixed(2)} MB</span>
            </div>
            <div class="file-status">✓ Ready <button class="trash-btn" data-index="${index}">🗑️</button></div>
        `;
        
        li.addEventListener('click', (e) => {
            if (e.target.classList.contains('trash-btn')) {
                uploadedFiles.splice(index, 1);
                renderFileList();
                if (uploadedFiles.length > 0) {
                    loadPreview(uploadedFiles[0]);
                } else {
                    document.getElementById('source-content').classList.add('hidden');
                    document.getElementById('drop-zone').classList.remove('compact');
                    updateWorkflowState("NO_REQUEST");
                }
                checkAnalyzeReadiness();
                e.stopPropagation();
                return;
            }
            loadPreview(file);
        });
        
        list.appendChild(li);
    });
    
    document.getElementById('file-count-text').innerText = `SOURCE AUDIO — ${uploadedFiles.length} FILE${uploadedFiles.length > 1 ? 'S' : ''}`;
}

function loadPreview(file) {
    document.getElementById('preview-filename').innerText = file.name;
    const fileUrl = URL.createObjectURL(file);
    originalWaveSurfer.load(fileUrl);
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
    btn.innerHTML = `<span class="spinner mr-2"></span> ANALYZING...`;
    document.getElementById('clarification-box').classList.add('hidden');
    
    // Show checklist pipeline
    const pipelineBox = document.getElementById('analysis-pipeline-box');
    const pipelineList = document.getElementById('analysis-progress-list');
    pipelineBox.classList.remove('hidden');
    
    const analysisSteps = ["Validating limits & security", "Profiling audio characteristics", "Extracting semantic intent", "Generating DSP transformation plan"];
    let currentStep = 0;
    
    const renderAnalysisPipeline = () => {
        pipelineList.innerHTML = '';
        analysisSteps.forEach((s, idx) => {
            const li = document.createElement('li');
            let iconHtml = '';
            if (idx < currentStep) {
                li.className = 'done';
                iconHtml = '<span class="status-icon" style="color: var(--success); font-weight: bold;">✓</span>';
            } else if (idx === currentStep) {
                li.className = 'active';
                iconHtml = '<span class="spinner" style="border-top-color: var(--accent-secondary); border-color: rgba(99, 102, 241, 0.3);"></span>';
            } else {
                li.className = 'pending';
                iconHtml = '<span class="status-icon" style="color: var(--border-color);">○</span>';
            }
            li.innerHTML = `${iconHtml} ${s}`;
            pipelineList.appendChild(li);
        });
    };
    renderAnalysisPipeline();
    
    // Simulate progression visually while fetch happens
    const simInterval = setInterval(() => {
        if (currentStep < 3) {
            currentStep++;
            renderAnalysisPipeline();
        }
    }, 2500);

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
            clearInterval(simInterval);
            pipelineBox.classList.add('hidden');
            return;
        }
        
        if (data.status === "PLAN_READY") {
            currentRequestId = data.request_id;
            
            // Populate Stage 3
            const select = document.getElementById('profile-file-select');
            select.innerHTML = '';
            window.currentInputProfiles = data.input_profiles;
            
            Object.keys(data.input_profiles).forEach(filename => {
                const opt = document.createElement('option');
                opt.value = filename;
                opt.innerText = filename;
                select.appendChild(opt);
            });
            
            select.onchange = () => {
                const selectedFile = select.value;
                const profile = window.currentInputProfiles[selectedFile];
                document.getElementById('kpi-duration').innerText = `${profile.file_info.duration.toFixed(1)}s`;
                document.getElementById('kpi-sr').innerText = `${(profile.file_info.sample_rate/1000).toFixed(1)} kHz`;
                document.getElementById('kpi-ch').innerText = profile.file_info.channels === 1 ? 'Mono' : 'Stereo';
                document.getElementById('kpi-snr').innerText = `${profile.noise.estimated_snr.toFixed(1)} dB`;
                document.getElementById('kpi-rms').innerText = `${profile.signal_quality.rms.toFixed(2)} dB`;
                document.getElementById('kpi-peak').innerText = `${profile.signal_quality.peak.toFixed(2)} dB`;
                document.getElementById('full-profile-json').innerText = JSON.stringify(profile, null, 2);
            };
            select.onchange(); // trigger initial population
            
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
            clearInterval(simInterval);
            pipelineBox.classList.add('hidden');
            
        }
        
    } catch (err) {
        clearInterval(simInterval);
        pipelineBox.classList.add('hidden');
        console.error(err);
        updateWorkflowState("PLAN_FAILED");
        showToast("Analysis Failed", "Could not analyze the audio and prompt. Please check your inputs and try again.", "error");
        btn.disabled = false;
        btn.innerText = "✨ ANALYZE & CREATE PLAN";
    }
}

async function handleApprove() {
    if (!currentRequestId) return;
    
    const approveBtn = document.getElementById('approve-btn');
    approveBtn.disabled = true;
    approveBtn.innerHTML = `<span class="spinner mr-2"></span> GENERATING...`;
    
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
                    let iconHtml = '';
                    if (idx < currentIndex) {
                        li.className = 'done';
                        iconHtml = '<span class="status-icon" style="color: var(--success); font-weight: bold;">✓</span>';
                    } else if (idx === currentIndex) {
                        li.className = 'active';
                        iconHtml = '<span class="spinner" style="border-top-color: var(--accent-secondary); border-color: rgba(99, 102, 241, 0.3);"></span>';
                    } else {
                        li.className = 'pending';
                        iconHtml = '<span class="status-icon" style="color: var(--border-color);">○</span>';
                    }
                    li.innerHTML = `${iconHtml} ${s.replace(/_/g, ' ')}`;
                    list.appendChild(li);
                }
            });
            
            if (data.status === "COMPLETED") {
                clearInterval(interval);
                populateResults(data.metadata);
            } else if (data.status === "PROCESSING_FAILED") {
                clearInterval(interval);
                showToast("Processing Failed", "An error occurred during audio generation. Please try again.", "error");
            }
            
        } catch (err) {
            console.error(err);
        }
    }, 1000);
}

function populateResults(metadata) {
    const select = document.getElementById('result-file-select');
    select.innerHTML = '';
    metadata.files.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f.original_filename;
        opt.innerText = f.original_filename;
        select.appendChild(opt);
    });

    select.onchange = () => {
        const selectedOriginalName = select.value;
        const fileOutput = metadata.files.find(f => f.original_filename === selectedOriginalName);
        
        document.getElementById('res-orig-file').innerText = fileOutput.original_filename;
        document.getElementById('res-aug-file').innerText = fileOutput.augmented_filename;
        
        if (!resOrigWaveSurfer) {
            resOrigWaveSurfer = WaveSurfer.create({ container: '#res-orig-waveform', waveColor: '#9CA3AF', progressColor: '#6366F1', height: 60, normalize: true });
            resAugWaveSurfer = WaveSurfer.create({ container: '#res-aug-waveform', waveColor: '#10B981', progressColor: '#3B82F6', height: 60, normalize: true });
            
            document.getElementById('play-res-orig').onclick = () => resOrigWaveSurfer.playPause();
            document.getElementById('play-res-aug').onclick = () => resAugWaveSurfer.playPause();
            
            resOrigWaveSurfer.on('play', () => document.getElementById('play-res-orig').innerText = '⏸ Pause');
            resOrigWaveSurfer.on('pause', () => document.getElementById('play-res-orig').innerText = '▶ Play');
            
            resAugWaveSurfer.on('play', () => document.getElementById('play-res-aug').innerText = '⏸ Pause');
            resAugWaveSurfer.on('pause', () => document.getElementById('play-res-aug').innerText = '▶ Play');
        }
        
        const baseUrl = "http://localhost:8000";
        resOrigWaveSurfer.load(baseUrl + fileOutput.original_uri);
        resAugWaveSurfer.load(baseUrl + fileOutput.augmented_uri);
        
        const inputProfile = metadata.input_profiles[fileOutput.original_filename];
        const outputProfile = metadata.output_profiles[fileOutput.original_filename];

        const tbody = document.getElementById('metrics-tbody');
        tbody.innerHTML = `
            <tr>
                <td>SNR</td>
                <td class="text-right">${inputProfile.noise.estimated_snr.toFixed(1)} dB</td>
                <td class="text-right">${outputProfile.noise.estimated_snr.toFixed(1)} dB</td>
                <td>✓</td>
            </tr>
            <tr>
                <td>RMS</td>
                <td class="text-right">${inputProfile.signal_quality.rms.toFixed(2)} dB</td>
                <td class="text-right">${outputProfile.signal_quality.rms.toFixed(2)} dB</td>
                <td>✓</td>
            </tr>
            <tr>
                <td>Peak</td>
                <td class="text-right">${inputProfile.signal_quality.peak.toFixed(2)} dB</td>
                <td class="text-right">${outputProfile.signal_quality.peak.toFixed(2)} dB</td>
                <td>✓</td>
            </tr>
        `;
        
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

        document.getElementById('download-audio-btn').onclick = () => {
            const a = document.createElement('a');
            a.href = baseUrl + fileOutput.augmented_uri;
            a.download = fileOutput.augmented_filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
        };
        
        document.getElementById('download-meta-btn').onclick = () => {
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(metadata, null, 2));
            const a = document.createElement('a');
            a.href = dataStr;
            a.download = "metadata.json";
            document.body.appendChild(a);
            a.click();
            a.remove();
        };
    };
    
    select.onchange();
}
