// export.js - PDF export and biography generation functions

// Utility function to escape HTML (security)
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// State management for biography
const biographyState = {
    selectedChapters: null,
    currentModel: null,
    originalTexts: {},
    hasUnsavedEdits: false
};

// ========================================
// PDF EXPORT FUNCTIONS
// ========================================

async function generatePDF(type = 'full') {
    const statusDiv = document.getElementById('export-status');
    statusDiv.innerHTML = `<div class="loading"><i class="fas fa-spinner fa-spin"></i> <p>Generating ${type === 'full' ? 'Complete' : 'Summary'} PDF...</p></div>`;
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout
        
        const response = await fetch(`/api/pdf/generate/${type}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = type === 'full' ? 'family_story_full.pdf' : 'family_story_summary.pdf';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            statusDiv.innerHTML = `<div style="color: #28a745; padding: 15px; background: #d4edda; border-radius: 8px;">
                <i class="fas fa-check-circle"></i> ${type === 'full' ? 'Complete' : 'Summary'} PDF generated successfully!
            </div>`;
        } else {
            const error = await response.json();
            statusDiv.innerHTML = `<div style="color: #dc3545; padding: 15px; background: #f8d7da; border-radius: 8px;">
                <i class="fas fa-exclamation-triangle"></i> Error: ${error.message || 'Unknown error'}
            </div>`;
        }
    } catch (error) {
        console.error('Error:', error);
        clearTimeout(timeoutId);
        
        if (error.name === 'AbortError') {
            statusDiv.innerHTML = `<div style="color: #dc3545; padding: 15px; background: #f8d7da; border-radius: 8px;">
                <i class="fas fa-exclamation-triangle"></i> Request timeout. The PDF is taking too long to generate.
            </div>`;
        } else {
            statusDiv.innerHTML = `<div style="color: #dc3545; padding: 15px; background: #f8d7da; border-radius: 8px;">
                <i class="fas fa-exclamation-triangle"></i> Failed to generate PDF. Make sure the server is running.
            </div>`;
        }
    }
}

async function generateFamilyAlbum() {
    const statusDiv = document.getElementById('export-status');
    statusDiv.innerHTML = `<div class="loading"><i class="fas fa-spinner fa-spin"></i> <p>Creating Family Album PDF...</p></div>`;
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000);
        
        const response = await fetch('/api/pdf/generate/album', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'family_album.pdf';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            statusDiv.innerHTML = `<div style="color: #28a745; padding: 15px; background: #d4edda; border-radius: 8px;">
                <i class="fas fa-check-circle"></i> Family Album PDF generated successfully!
            </div>`;
        } else {
            const error = await response.json();
            statusDiv.innerHTML = `<div style="color: #dc3545; padding: 15px; background: #f8d7da; border-radius: 8px;">
                <i class="fas fa-exclamation-triangle"></i> Error: ${error.message || 'Unknown error'}
            </div>`;
        }
    } catch (error) {
        console.error('Error:', error);
        clearTimeout(timeoutId);
        
        if (error.name === 'AbortError') {
            statusDiv.innerHTML = `<div style="color: #dc3545; padding: 15px; background: #f8d7da; border-radius: 8px;">
                <i class="fas fa-exclamation-triangle"></i> Request timeout. The album is taking too long to generate.
            </div>`;
        } else {
            statusDiv.innerHTML = `<div style="color: #dc3545; padding: 15px; background: #f8d7da; border-radius: 8px;">
                <i class="fas fa-exclamation-triangle"></i> Failed to generate family album.
            </div>`;
        }
    }
}

// ========================================
// BIOGRAPHY GENERATION FUNCTIONS
// ========================================

async function generateBiography(model = 'both') {
    try {
        // Reset state
        biographyState.hasUnsavedEdits = false;
        biographyState.originalTexts = {};
        
        // Show loading modal
        showBiographyLoading();
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minute timeout
        
        const response = await fetch('/api/export/biography/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({model: model}),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        const data = await response.json();
        
        if (data.status === 'success') {
            displayBiographyPreview(data);
        } else {
            showBiographyError('Error generating biography: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error generating biography:', error);
        clearTimeout(timeoutId);
        
        if (error.name === 'AbortError') {
            showBiographyError('Request timeout. The AI models are taking too long to respond.');
        } else {
            showBiographyError('Error generating biography. Please try again.');
        }
    }
}

function showBiographyLoading() {
    const modal = document.getElementById('biography-preview-modal');
    if (!modal) {
        console.error('Biography preview modal not found');
        return;
    }
    
    modal.style.display = 'flex';
    
    const content = modal.querySelector('.biography-preview-content') || modal;
    content.innerHTML = `
        <div class="biography-loading">
            <i class="fas fa-spinner fa-spin fa-3x"></i>
            <p>Generating biography with AI...</p>
            <p>This may take 30-60 seconds. Both DeepSeek and Claude are analyzing your memories and crafting narratives.</p>
            <div class="progress-container" style="margin-top: 20px; width: 80%; max-width: 400px;">
                <div class="progress-bar" style="height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden;">
                    <div class="progress-fill" style="height: 100%; width: 0%; background: #0066cc; transition: width 2s ease-in-out;"></div>
                </div>
            </div>
        </div>
    `;
    
    // Animate progress bar
    setTimeout(() => {
        const fill = content.querySelector('.progress-fill');
        if (fill) fill.style.width = '60%';
    }, 100);
}

function showBiographyError(message) {
    const modal = document.getElementById('biography-preview-modal');
    if (!modal) {
        alert(message);
        return;
    }
    
    const content = modal.querySelector('.biography-preview-content') || modal;
    
    content.innerHTML = `
        <div class="biography-error" style="padding: 30px; text-align: center;">
            <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #dc3545; margin-bottom: 20px;"></i>
            <h3 style="color: #721c24; margin-bottom: 15px;">Error</h3>
            <p style="color: #721c24; margin-bottom: 25px;">${escapeHtml(message)}</p>
            <div style="text-align: center; margin-top: 20px;">
                <button class="btn btn-secondary" onclick="closeBiographyPreview()">
                    Close
                </button>
                <button class="btn btn-primary" onclick="generateBiography('both')" style="margin-left: 10px;">
                    <i class="fas fa-redo"></i> Try Again
                </button>
            </div>
        </div>
    `;
}

function displayBiographyPreview(data) {
    // Validate data
    if (!data || (!data.deepseek && !data.claude)) {
        showBiographyError('No biography data received from server.');
        return;
    }
    
    // Reset modal content
    const modal = document.getElementById('biography-preview-modal');
    modal.innerHTML = `
        <div class="modal-content biography-preview-content">
            <div class="modal-header">
                <h2><i class="fas fa-book"></i> Biography Preview - Compare Versions</h2>
                <button class="close-btn" onclick="closeBiographyPreview()">&times;</button>
            </div>
            
            <div class="model-selector">
                <button id="show-deepseek" class="btn btn-secondary active" onclick="showVersion('deepseek')">
                    <i class="fas fa-robot"></i> DeepSeek Version
                </button>
                <button id="show-claude" class="btn btn-secondary" onclick="showVersion('claude')">
                    <i class="fas fa-brain"></i> Claude Version
                </button>
                <button id="show-both" class="btn btn-secondary" onclick="showVersion('both')">
                    <i class="fas fa-columns"></i> Side by Side
                </button>
            </div>
            
            <div id="biography-content" class="biography-content">
                <!-- DeepSeek version -->
                <div id="deepseek-version" class="version-panel">
                    <div class="version-header">
                        <h3><i class="fas fa-robot"></i> DeepSeek Generated Biography</h3>
                        <span class="chapter-count" id="deepseek-count"></span>
                    </div>
                    <div id="deepseek-chapters" class="chapters-container"></div>
                </div>
                
                <!-- Claude version -->
                <div id="claude-version" class="version-panel">
                    <div class="version-header">
                        <h3><i class="fas fa-brain"></i> Claude Generated Biography</h3>
                        <span class="chapter-count" id="claude-count"></span>
                    </div>
                    <div id="claude-chapters" class="chapters-container"></div>
                </div>
            </div>
            
            <div class="biography-actions">
                <div class="action-buttons">
                    <button class="btn btn-primary" onclick="selectVersion('deepseek')">
                        <i class="fas fa-check"></i> Use DeepSeek Version
                    </button>
                    <button class="btn btn-primary" onclick="selectVersion('claude')">
                        <i class="fas fa-check"></i> Use Claude Version
                    </button>
                    <button class="btn btn-secondary" onclick="regenerateBiography()">
                        <i class="fas fa-sync"></i> Regenerate Both
                    </button>
                    <button class="btn btn-secondary" onclick="closeBiographyPreview()">
                        <i class="fas fa-times"></i> Cancel
                    </button>
                </div>
                <div class="unsaved-warning" id="unsaved-warning" style="display: none; color: #856404; background: #fff3cd; padding: 10px; border-radius: 4px; margin-top: 10px;">
                    <i class="fas fa-exclamation-triangle"></i> You have unsaved edits. Save or regenerate to preserve changes.
                </div>
            </div>
        </div>
    `;
    
    // Display DeepSeek version
    if (data.deepseek && !data.deepseek.error) {
        displayVersion('deepseek', data.deepseek.chapters || []);
    } else if (data.deepseek && data.deepseek.error) {
        document.getElementById('deepseek-chapters').innerHTML = `
            <div class="biography-error">
                <i class="fas fa-exclamation-triangle"></i>
                Error: ${escapeHtml(data.deepseek.error)}
            </div>
        `;
    } else {
        document.getElementById('deepseek-chapters').innerHTML = `
            <div class="biography-info">
                <i class="fas fa-info-circle"></i>
                DeepSeek version not available.
            </div>
        `;
    }
    
    // Display Claude version
    if (data.claude && !data.claude.error) {
        displayVersion('claude', data.claude.chapters || []);
    } else if (data.claude && data.claude.error) {
        document.getElementById('claude-chapters').innerHTML = `
            <div class="biography-error">
                <i class="fas fa-exclamation-triangle"></i>
                Error: ${escapeHtml(data.claude.error)}
            </div>
        `;
    } else {
        document.getElementById('claude-chapters').innerHTML = `
            <div class="biography-info">
                <i class="fas fa-info-circle"></i>
                Claude version not available.
            </div>
        `;
    }
    
    // Update chapter counts
    updateChapterCounts();
    
    // Show both versions by default
    showVersion('both');
}

function displayVersion(model, chapters) {
    const container = document.getElementById(`${model}-chapters`);
    const countElement = document.getElementById(`${model}-count`);
    
    if (!chapters || chapters.length === 0) {
        container.innerHTML = '<div class="biography-info"><p>No chapters generated.</p></div>';
        if (countElement) countElement.textContent = '(0 chapters)';
        return;
    }
    
    if (countElement) {
        countElement.textContent = `(${chapters.length} chapter${chapters.length !== 1 ? 's' : ''})`;
    }
    
    let html = '';
    chapters.forEach((chapter, index) => {
        const chapterId = `${model}-chapter-${index}`;
        biographyState.originalTexts[chapterId] = chapter.narrative || '';
        
        html += `
            <div class="chapter-preview" data-chapter="${index}" id="${chapterId}">
                <div class="chapter-header">
                    <h4>${escapeHtml(chapter.title || `Chapter ${index + 1}`)}</h4>
                    <div class="chapter-actions">
                        <button class="btn btn-sm btn-outline chapter-edit-btn" onclick="editChapter('${model}', ${index})">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                    </div>
                </div>
                <div class="chapter-narrative">${escapeHtml(chapter.narrative || '')}</div>
                <div class="chapter-footer">
                    <small>${(chapter.narrative || '').length} characters</small>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function updateChapterCounts() {
    const deepseekChapters = document.querySelectorAll('#deepseek-chapters .chapter-preview').length;
    const claudeChapters = document.querySelectorAll('#claude-chapters .chapter-preview').length;
    
    document.getElementById('deepseek-count').textContent = `(${deepseekChapters} chapter${deepseekChapters !== 1 ? 's' : ''})`;
    document.getElementById('claude-count').textContent = `(${claudeChapters} chapter${claudeChapters !== 1 ? 's' : ''})`;
}

function showVersion(view) {
    const content = document.getElementById('biography-content');
    const deepseek = document.getElementById('deepseek-version');
    const claude = document.getElementById('claude-version');
    
    if (!content || !deepseek || !claude) return;
    
    // Update button states
    document.querySelectorAll('.model-selector button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeBtn = document.getElementById(`show-${view}`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    
    if (view === 'both') {
        content.classList.remove('single-view');
        deepseek.classList.remove('active');
        claude.classList.remove('active');
    } else {
        content.classList.add('single-view');
        deepseek.classList.toggle('active', view === 'deepseek');
        claude.classList.toggle('active', view === 'claude');
    }
}

async function selectVersion(model) {
    if (biographyState.hasUnsavedEdits && !confirm('You have unsaved edits. Save this version anyway?')) {
        return;
    }
    
    const chapters = [];
    const chapterElements = document.querySelectorAll(`#${model}-chapters .chapter-preview`);
    
    if (chapterElements.length === 0) {
        alert('No chapters to save for this version.');
        return;
    }
    
    chapterElements.forEach((el, index) => {
        chapters.push({
            title: el.querySelector('h4')?.textContent || `Chapter ${index + 1}`,
            narrative: el.querySelector('.chapter-narrative')?.textContent || ''
        });
    });
    
    // Validate chapters
    if (!validateChapters(chapters)) {
        alert('Some chapters are empty. Please edit them before saving.');
        return;
    }
    
    try {
        // Save selected version
        const response = await fetch('/api/export/biography/save-edits', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                chapters: chapters,
                model: model
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            biographyState.selectedChapters = chapters;
            biographyState.currentModel = model;
            biographyState.hasUnsavedEdits = false;
            
            showBiographyPDFOption(model, chapters);
        } else {
            throw new Error(data.message || 'Unknown error');
        }
    } catch (error) {
        console.error('Error saving version:', error);
        alert('Error saving selection: ' + error.message);
    }
}

function editChapter(model, chapterIndex) {
    const chapterId = `${model}-chapter-${chapterIndex}`;
    const chapterEl = document.getElementById(chapterId);
    
    if (!chapterEl) {
        console.error('Chapter element not found:', chapterId);
        return;
    }
    
    const narrativeEl = chapterEl.querySelector('.chapter-narrative');
    const editBtn = chapterEl.querySelector('.chapter-edit-btn');
    const footerEl = chapterEl.querySelector('.chapter-footer');
    
    if (!narrativeEl || !editBtn) {
        console.error('Required elements not found in chapter');
        return;
    }
    
    // Save original text if not already saved
    const currentText = narrativeEl.textContent;
    if (!biographyState.originalTexts[chapterId]) {
        biographyState.originalTexts[chapterId] = currentText;
    }
    
    // Create edit interface
    const textareaId = `edit-${chapterId}`;
    narrativeEl.innerHTML = `
        <div class="edit-container">
            <textarea id="${textareaId}" class="chapter-edit-area" rows="6">${escapeHtml(currentText)}</textarea>
            <div class="edit-actions">
                <button class="btn btn-sm btn-primary" onclick="saveChapterEdit('${model}', ${chapterIndex})">
                    <i class="fas fa-save"></i> Save
                </button>
                <button class="btn btn-sm btn-secondary" onclick="cancelChapterEdit('${model}', ${chapterIndex})">
                    <i class="fas fa-times"></i> Cancel
                </button>
                <span class="char-count" id="char-count-${chapterId}">${currentText.length} characters</span>
            </div>
        </div>
    `;
    
    // Hide edit button and footer
    editBtn.style.display = 'none';
    if (footerEl) footerEl.style.display = 'none';
    
    // Add character count listener
    const textarea = document.getElementById(textareaId);
    const charCount = document.getElementById(`char-count-${chapterId}`);
    
    textarea.addEventListener('input', function() {
        if (charCount) {
            charCount.textContent = this.value.length + ' characters';
        }
        biographyState.hasUnsavedEdits = true;
        updateUnsavedWarning();
    });
    
    // Focus textarea
    textarea.focus();
}

function saveChapterEdit(model, chapterIndex) {
    const chapterId = `${model}-chapter-${chapterIndex}`;
    const chapterEl = document.getElementById(chapterId);
    
    if (!chapterEl) return;
    
    const textarea = chapterEl.querySelector('textarea');
    const narrativeEl = chapterEl.querySelector('.chapter-narrative');
    const editBtn = chapterEl.querySelector('.chapter-edit-btn');
    const footerEl = chapterEl.querySelector('.chapter-footer');
    
    if (!textarea || !narrativeEl || !editBtn) return;
    
    const newText = textarea.value;
    narrativeEl.textContent = newText;
    
    // Show edit button and footer again
    editBtn.style.display = 'block';
    if (footerEl) {
        footerEl.style.display = 'block';
        footerEl.querySelector('small').textContent = newText.length + ' characters';
    }
    
    // Update original text
    biographyState.originalTexts[chapterId] = newText;
}

function cancelChapterEdit(model, chapterIndex) {
    const chapterId = `${model}-chapter-${chapterIndex}`;
    const chapterEl = document.getElementById(chapterId);
    
    if (!chapterEl) return;
    
    const narrativeEl = chapterEl.querySelector('.chapter-narrative');
    const editBtn = chapterEl.querySelector('.chapter-edit-btn');
    const footerEl = chapterEl.querySelector('.chapter-footer');
    
    if (!narrativeEl || !editBtn) return;
    
    // Restore original text
    const originalText = biographyState.originalTexts[chapterId] || '';
    narrativeEl.textContent = originalText;
    
    // Show edit button and footer again
    editBtn.style.display = 'block';
    if (footerEl) {
        footerEl.style.display = 'block';
        footerEl.querySelector('small').textContent = originalText.length + ' characters';
    }
    
    // Clear unsaved edits if this was the only edit
    checkUnsavedEdits();
}

function updateUnsavedWarning() {
    const warning = document.getElementById('unsaved-warning');
    if (warning) {
        warning.style.display = biographyState.hasUnsavedEdits ? 'block' : 'none';
    }
}

function checkUnsavedEdits() {
    // Check if any chapter has been edited
    biographyState.hasUnsavedEdits = false;
    updateUnsavedWarning();
}

function validateChapters(chapters) {
    if (!Array.isArray(chapters)) return false;
    
    return chapters.every(chapter => 
        chapter && 
        typeof chapter.title === 'string' && 
        chapter.title.trim().length > 0 &&
        typeof chapter.narrative === 'string' && 
        chapter.narrative.trim().length > 0
    );
}

function regenerateBiography() {
    if (biographyState.hasUnsavedEdits) {
        if (!confirm('You have unsaved edits. Regenerating will lose all changes. Continue?')) {
            return;
        }
    }
    
    generateBiography('both');
}

function closeBiographyPreview() {
    if (biographyState.hasUnsavedEdits) {
        if (!confirm('You have unsaved edits. Are you sure you want to close?')) {
            return;
        }
    }
    
    const modal = document.getElementById('biography-preview-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    
    // Reset state
    biographyState.hasUnsavedEdits = false;
    biographyState.originalTexts = {};
}

function showBiographyPDFOption(model, chapters) {
    const modal = document.getElementById('biography-preview-modal');
    if (!modal) return;
    
    const actions = modal.querySelector('.biography-actions');
    if (!actions) return;
    
    // Update actions area
    actions.innerHTML = `
        <div class="selection-success">
            <i class="fas fa-check-circle"></i>
            <div class="success-message">
                <strong>${model === 'deepseek' ? 'DeepSeek' : 'Claude'} version selected!</strong>
                <p>Ready to generate your magazine-style PDF with photos.</p>
            </div>
        </div>
        
        <div class="pdf-options">
            <h4>PDF Customization</h4>
            <div class="option-group">
                <label for="pdf-title">Title:</label>
                <input type="text" id="pdf-title" value="The Making of a Life" class="form-control">
            </div>
            <div class="option-group">
                <label for="pdf-subtitle">Subtitle:</label>
                <input type="text" id="pdf-subtitle" value="A Family Story" class="form-control">
            </div>
            <div class="option-group">
                <label>
                    <input type="checkbox" id="include-photos" checked> Include photos from memories
                </label>
            </div>
            
            <div class="action-buttons" style="margin-top: 20px;">
                <button class="btn btn-primary" onclick="customizeBiographyPDF()">
                    <i class="fas fa-book"></i> Generate PDF
                </button>
                <button class="btn btn-secondary" onclick="displayBiographyPreview({deepseek: {chapters: window.selectedBiographyChapters}, claude: {chapters: []}})">
                    <i class="fas fa-arrow-left"></i> Back to Preview
                </button>
                <button class="btn btn-secondary" onclick="regenerateBiography()">
                    <i class="fas fa-sync"></i> Start Over
                </button>
            </div>
        </div>
    `;
    
    // Store chapters for PDF generation
    window.selectedBiographyChapters = chapters;
    biographyState.currentModel = model;
}

function customizeBiographyPDF() {
    const titleInput = document.getElementById('pdf-title');
    const subtitleInput = document.getElementById('pdf-subtitle');
    const includePhotos = document.getElementById('include-photos');
    
    if (!titleInput || !subtitleInput) {
        alert('Please fill in all fields.');
        return;
    }
    
    const title = titleInput.value.trim();
    const subtitle = subtitleInput.value.trim();
    const includePhotosFlag = includePhotos ? includePhotos.checked : true;
    
    if (!title) {
        alert('Please enter a title for your biography.');
        return;
    }
    
    generateBiographyPDF(window.selectedBiographyChapters, title, subtitle, includePhotosFlag);
}

async function generateBiographyPDF(chapters, title, subtitle, includePhotos = true) {
    try {
        // Show loading
        const modal = document.getElementById('biography-preview-modal');
        const actions = modal.querySelector('.biography-actions');
        
        if (actions) {
            actions.innerHTML = `
                <div class="pdf-generating">
                    <i class="fas fa-spinner fa-spin fa-3x"></i>
                    <h4>Generating PDF</h4>
                    <p>Creating magazine-style biography with ${includePhotos ? 'photos' : 'text only'}...</p>
                    <div class="progress-info">
                        <div class="progress">
                            <div class="progress-bar" style="width: 0%"></div>
                        </div>
                        <p class="progress-text">Initializing...</p>
                    </div>
                    <p class="time-estimate">This may take 30-60 seconds</p>
                </div>
            `;
            
            // Simulate progress
            const progressBar = actions.querySelector('.progress-bar');
            const progressText = actions.querySelector('.progress-text');
            
            const updateProgress = (percent, text) => {
                if (progressBar) progressBar.style.width = percent + '%';
                if (progressText) progressText.textContent = text;
            };
            
            setTimeout(() => updateProgress(25, 'Processing chapters...'), 1000);
            setTimeout(() => updateProgress(50, 'Formatting content...'), 3000);
            setTimeout(() => updateProgress(75, includePhotos ? 'Adding photos...' : 'Finalizing layout...'), 6000);
        }
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 180000); // 3 minute timeout
        
        const response = await fetch('/api/export/biography/pdf', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                chapters: chapters,
                title: title,
                subtitle: subtitle,
                includePhotos: includePhotos,
                model: biographyState.currentModel
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${title.replace(/\s+/g, '_').toLowerCase()}_biography.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            // Show success
            if (actions) {
                actions.innerHTML = `
                    <div class="pdf-success">
                        <i class="fas fa-check-circle"></i>
                        <h4>PDF Generated Successfully!</h4>
                        <p>Your biography PDF has been downloaded.</p>
                        <div class="success-actions">
                            <button class="btn btn-primary" onclick="generateBiographyPDF(window.selectedBiographyChapters, '${escapeHtml(title)}', '${escapeHtml(subtitle)}', ${includePhotos})">
                                <i class="fas fa-download"></i> Download Again
                            </button>
                            <button class="btn btn-secondary" onclick="closeBiographyPreview()">
                                <i class="fas fa-times"></i> Close
                            </button>
                            <button class="btn btn-outline" onclick="generateBiography('both')" style="margin-top: 10px;">
                                <i class="fas fa-plus"></i> Create Another Biography
                            </button>
                        </div>
                    </div>
                `;
            }
        } else {
            const error = await response.json();
            throw new Error(error.message || 'Unknown error generating PDF');
        }
    } catch (error) {
        console.error('Error generating PDF:', error);
        
        const modal = document.getElementById('biography-preview-modal');
        const actions = modal?.querySelector('.biography-actions');
        
        if (actions) {
            actions.innerHTML = `
                <div class="pdf-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h4>Error Generating PDF</h4>
                    <p>${escapeHtml(error.message || 'Failed to generate PDF. Please try again.')}</p>
                    <div class="error-actions">
                        <button class="btn btn-primary" onclick="customizeBiographyPDF()">
                            <i class="fas fa-redo"></i> Try Again
                        </button>
                        <button class="btn btn-secondary" onclick="closeBiographyPreview()">
                            Close
                        </button>
                    </div>
                </div>
            `;
        } else {
            alert('Error generating PDF: ' + error.message);
        }
    }
}

// ========================================
// MAKE FUNCTIONS GLOBALLY AVAILABLE
// ========================================

window.generatePDF = generatePDF;
window.generateFamilyAlbum = generateFamilyAlbum;
window.generateBiography = generateBiography;
window.showVersion = showVersion;
window.selectVersion = selectVersion;
window.editChapter = editChapter;
window.saveChapterEdit = saveChapterEdit;
window.cancelChapterEdit = cancelChapterEdit;
window.regenerateBiography = regenerateBiography;
window.closeBiographyPreview = closeBiographyPreview;
window.customizeBiographyPDF = customizeBiographyPDF;
window.generateBiographyPDF = generateBiographyPDF;
window.escapeHtml = escapeHtml; // Make utility function available globally