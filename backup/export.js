// export.js - PDF export functions
async function generatePDF(type = 'full') {
    const statusDiv = document.getElementById('export-status');
    statusDiv.innerHTML = `<div class="loading"><i class="fas fa-spinner fa-spin"></i> <p>Generating ${type === 'full' ? 'Complete' : 'Summary'} PDF...</p></div>`;
    
    try {
        const response = await fetch(`/api/pdf/generate/${type}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
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
        statusDiv.innerHTML = `<div style="color: #dc3545; padding: 15px; background: #f8d7da; border-radius: 8px;">
            <i class="fas fa-exclamation-triangle"></i> Failed to generate PDF. Make sure the server is running.
        </div>`;
    }
}

async function generateFamilyAlbum() {
    const statusDiv = document.getElementById('export-status');
    statusDiv.innerHTML = `<div class="loading"><i class="fas fa-spinner fa-spin"></i> <p>Creating Family Album PDF...</p></div>`;
    
    try {
        const response = await fetch('/api/pdf/generate/album', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
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
        statusDiv.innerHTML = `<div style="color: #dc3545; padding: 15px; background: #f8d7da; border-radius: 8px;">
            <i class="fas fa-exclamation-triangle"></i> Failed to generate family album.
        </div>`;
    }
}

/* ========================================
   ADD TO static/js/export.js
   BIOGRAPHY GENERATION FUNCTIONS
   ======================================== */

// Biography generation and preview functions

async function generateBiography(model = 'both') {
    try {
        // Show loading modal
        showBiographyLoading();
        
        const response = await fetch('/api/export/biography/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({model: model})
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayBiographyPreview(data);
        } else {
            showBiographyError('Error generating biography: ' + data.message);
        }
    } catch (error) {
        console.error('Error generating biography:', error);
        showBiographyError('Error generating biography. Please try again.');
    }
}

function showBiographyLoading() {
    const modal = document.getElementById('biography-preview-modal');
    modal.style.display = 'flex';
    
    const content = modal.querySelector('.biography-preview-content');
    content.innerHTML = `
        <div class="biography-loading">
            <i class="fas fa-spinner fa-spin fa-3x"></i>
            <p>Generating biography with AI...</p>
            <p>This may take 30-60 seconds. Both DeepSeek and Claude are analyzing your memories and crafting narratives.</p>
        </div>
    `;
}

function showBiographyError(message) {
    const modal = document.getElementById('biography-preview-modal');
    const content = modal.querySelector('.biography-preview-content');
    
    content.innerHTML = `
        <div class="biography-error">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Error:</strong> ${message}
        </div>
        <div style="text-align: center; margin-top: 20px;">
            <button class="btn btn-secondary" onclick="closeBiographyPreview()">
                Close
            </button>
        </div>
    `;
}

function displayBiographyPreview(data) {
    // Reset modal content
    const modal = document.getElementById('biography-preview-modal');
    modal.innerHTML = `
        <div class="modal-content biography-preview-content">
            <h2><i class="fas fa-book"></i> Biography Preview - Compare Versions</h2>
            
            <div class="model-selector">
                <button id="show-deepseek" class="btn btn-secondary active" onclick="showVersion('deepseek')">
                    DeepSeek Version
                </button>
                <button id="show-claude" class="btn btn-secondary" onclick="showVersion('claude')">
                    Claude Version
                </button>
                <button id="show-both" class="btn btn-secondary" onclick="showVersion('both')">
                    Side by Side
                </button>
            </div>
            
            <div id="biography-content" class="biography-content">
                <!-- DeepSeek version -->
                <div id="deepseek-version" class="version-panel">
                    <h3>DeepSeek Generated Biography</h3>
                    <div id="deepseek-chapters" class="chapters-container"></div>
                </div>
                
                <!-- Claude version -->
                <div id="claude-version" class="version-panel">
                    <h3>Claude Generated Biography</h3>
                    <div id="claude-chapters" class="chapters-container"></div>
                </div>
            </div>
            
            <div class="biography-actions">
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
        </div>
    `;
    
    // Display DeepSeek version
    if (data.deepseek && !data.deepseek.error) {
        displayVersion('deepseek', data.deepseek.chapters);
    } else if (data.deepseek && data.deepseek.error) {
        document.getElementById('deepseek-chapters').innerHTML = `
            <div class="biography-error">
                <i class="fas fa-exclamation-triangle"></i>
                Error: ${data.deepseek.error}
            </div>
        `;
    }
    
    // Display Claude version
    if (data.claude && !data.claude.error) {
        displayVersion('claude', data.claude.chapters);
    } else if (data.claude && data.claude.error) {
        document.getElementById('claude-chapters').innerHTML = `
            <div class="biography-error">
                <i class="fas fa-exclamation-triangle"></i>
                Error: ${data.claude.error}
            </div>
        `;
    }
    
    // Show both versions by default
    showVersion('both');
}

function displayVersion(model, chapters) {
    const container = document.getElementById(`${model}-chapters`);
    
    if (!chapters || chapters.length === 0) {
        container.innerHTML = '<p>No chapters generated.</p>';
        return;
    }
    
    let html = '';
    chapters.forEach((chapter, index) => {
        html += `
            <div class="chapter-preview" data-chapter="${index}">
                <h4>${escapeHtml(chapter.title)}</h4>
                <div class="chapter-narrative">${escapeHtml(chapter.narrative)}</div>
                <button class="btn btn-sm chapter-edit-btn" onclick="editChapter('${model}', ${index})">
                    <i class="fas fa-edit"></i> Edit Chapter
                </button>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function showVersion(view) {
    const content = document.getElementById('biography-content');
    const deepseek = document.getElementById('deepseek-version');
    const claude = document.getElementById('claude-version');
    
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

function selectVersion(model) {
    const chapters = Array.from(document.querySelectorAll(`#${model}-chapters .chapter-preview`))
        .map(el => ({
            title: el.querySelector('h4').textContent,
            narrative: el.querySelector('.chapter-narrative').textContent
        }));
    
    if (chapters.length === 0) {
        alert('No chapters to save.');
        return;
    }
    
    // Save selected version
    fetch('/api/export/biography/save-edits', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            chapters: chapters,
            model: model
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Show success message and PDF download option
            showBiographyPDFOption(model, chapters);
        } else {
            alert('Error saving: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error saving version:', error);
        alert('Error saving selection. Please try again.');
    });
}

function editChapter(model, chapterIndex) {
    const chapterEl = document.querySelector(`#${model}-chapters .chapter-preview[data-chapter="${chapterIndex}"]`);
    const narrativeEl = chapterEl.querySelector('.chapter-narrative');
    const editBtn = chapterEl.querySelector('.chapter-edit-btn');
    
    // Save original text
    const currentText = narrativeEl.textContent;
    
    // Replace with editable textarea
    narrativeEl.innerHTML = `
        <textarea class="chapter-edit-area">${escapeHtml(currentText)}</textarea>
        <button class="btn btn-sm btn-primary" onclick="saveChapterEdit('${model}', ${chapterIndex})">
            <i class="fas fa-save"></i> Save
        </button>
        <button class="btn btn-sm btn-secondary" onclick="cancelChapterEdit('${model}', ${chapterIndex}, \`${currentText.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`)">
            <i class="fas fa-times"></i> Cancel
        </button>
    `;
    
    // Hide edit button while editing
    editBtn.style.display = 'none';
}

function saveChapterEdit(model, chapterIndex) {
    const chapterEl = document.querySelector(`#${model}-chapters .chapter-preview[data-chapter="${chapterIndex}"]`);
    const textarea = chapterEl.querySelector('textarea');
    const narrativeEl = chapterEl.querySelector('.chapter-narrative');
    const editBtn = chapterEl.querySelector('.chapter-edit-btn');
    
    const newText = textarea.value;
    narrativeEl.textContent = newText;
    
    // Show edit button again
    editBtn.style.display = 'block';
}

function cancelChapterEdit(model, chapterIndex, originalText) {
    const chapterEl = document.querySelector(`#${model}-chapters .chapter-preview[data-chapter="${chapterIndex}"]`);
    const narrativeEl = chapterEl.querySelector('.chapter-narrative');
    const editBtn = chapterEl.querySelector('.chapter-edit-btn');
    
    narrativeEl.textContent = originalText;
    
    // Show edit button again
    editBtn.style.display = 'block';
}

function regenerateBiography() {
    if (confirm('Regenerate both biography versions?\n\nCurrent edits will be lost.')) {
        generateBiography('both');
    }
}

function closeBiographyPreview() {
    document.getElementById('biography-preview-modal').style.display = 'none';
}

## ADD THESE NEW FUNCTIONS TO export.js:

function showBiographyPDFOption(model, chapters) {
    const modal = document.getElementById('biography-preview-modal');
    const actions = modal.querySelector('.biography-actions');
    
    // Update actions area
    actions.innerHTML = `
        <div style="text-align: center; width: 100%; padding: 20px; background: #d4edda; border-radius: 8px; margin-bottom: 20px;">
            <i class="fas fa-check-circle" style="color: #28a745; font-size: 24px;"></i>
            <p style="margin: 10px 0; font-size: 16px; color: #155724;">
                <strong>${model === 'deepseek' ? 'DeepSeek' : 'Claude'} version selected!</strong>
            </p>
            <p style="margin: 0; color: #155724;">
                Ready to generate your magazine-style PDF with photos.
            </p>
        </div>
        
        <div style="text-align: center; width: 100%;">
            <button class="btn btn-primary" onclick="customizeBiographyPDF()" style="min-width: 250px; font-size: 16px;">
                <i class="fas fa-book"></i> Customize & Download PDF
            </button>
            <button class="btn btn-secondary" onclick="regenerateBiography()">
                <i class="fas fa-sync"></i> Start Over
            </button>
            <button class="btn btn-secondary" onclick="closeBiographyPreview()">
                <i class="fas fa-times"></i> Close
            </button>
        </div>
    `;
    
    // Store chapters in window for PDF generation
    window.selectedBiographyChapters = chapters;
}

function customizeBiographyPDF() {
    // Show customization dialog
    const title = prompt('Biography Title:', 'The Making of a Life');
    if (!title) return;
    
    const subtitle = prompt('Subtitle:', 'A Family Story');
    if (!subtitle) return;
    
    // Generate PDF
    generateBiographyPDF(window.selectedBiographyChapters, title, subtitle);
}

async function generateBiographyPDF(chapters, title, subtitle) {
    try {
        // Show loading
        const modal = document.getElementById('biography-preview-modal');
        const actions = modal.querySelector('.biography-actions');
        
        actions.innerHTML = `
            <div style="text-align: center; width: 100%; padding: 40px;">
                <i class="fas fa-spinner fa-spin fa-3x" style="color: #0066cc;"></i>
                <p style="margin-top: 20px; font-size: 16px;">
                    Generating magazine-style PDF with photos...
                </p>
                <p style="color: #666;">
                    This may take 30-60 seconds
                </p>
            </div>
        `;
        
        const response = await fetch('/api/export/biography/pdf', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                chapters: chapters,
                title: title,
                subtitle: subtitle
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${title.replace(/\s+/g, '_').toLowerCase()}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            // Show success
            actions.innerHTML = `
                <div style="text-align: center; width: 100%; padding: 20px;">
                    <i class="fas fa-check-circle" style="color: #28a745; font-size: 32px;"></i>
                    <p style="margin: 15px 0; font-size: 18px; color: #28a745;">
                        <strong>PDF Generated Successfully!</strong>
                    </p>
                    <p style="color: #666; margin-bottom: 20px;">
                        Your biography PDF has been downloaded
                    </p>
                    <button class="btn btn-primary" onclick="generateBiographyPDF(window.selectedBiographyChapters, '${title}', '${subtitle}')">
                        <i class="fas fa-download"></i> Download Again
                    </button>
                    <button class="btn btn-secondary" onclick="closeBiographyPreview()">
                        <i class="fas fa-times"></i> Close
                    </button>
                </div>
            `;
        } else {
            const error = await response.json();
            actions.innerHTML = `
                <div style="text-align: center; width: 100%; padding: 20px; background: #f8d7da; border-radius: 8px;">
                    <i class="fas fa-exclamation-triangle" style="color: #dc3545; font-size: 24px;"></i>
                    <p style="margin: 10px 0; color: #721c24;">
                        <strong>Error generating PDF:</strong> ${error.message || 'Unknown error'}
                    </p>
                    <button class="btn btn-secondary" onclick="closeBiographyPreview()">
                        Close
                    </button>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error generating PDF:', error);
        alert('Error generating PDF. Please try again.');
    }
}

// Make functions globally available
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
