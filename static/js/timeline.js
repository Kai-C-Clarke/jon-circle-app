// timeline.js - Timeline functions with DELETE and EDIT functionality

async function loadMemories() {
    try {
        const response = await fetch('/api/memories/get');
        const data = await response.json();
        const memories = data.memories || [];
        
        const container = document.getElementById('timeline-content');
        
        if (!memories || memories.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-book-open fa-3x"></i>
                    <h3>No Memories Yet</h3>
                    <p>Start by sharing your first family story!</p>
                    <button onclick="showTab('capture')" class="btn-primary">
                        <i class="fas fa-plus-circle"></i> Share a Memory
                    </button>
                </div>
            `;
            return;
        }
        
        let html = '';
        memories.forEach(memory => {
            html += `
                <div class="memory-card" data-id="${memory.id}">
                    <div class="memory-header">
                        <div>
                            <span class="memory-year">${memory.year || 'Unknown year'}</span>
                            <span class="memory-category">${memory.category || 'memory'}</span>
                        </div>
                        <div class="memory-actions">
                            <button onclick="editMemory(${memory.id})" class="btn-icon" title="Edit this memory">
                                <i class="fas fa-pencil-alt"></i>
                            </button>
                            <button onclick="deleteMemory(${memory.id})" class="delete-btn" title="Delete this memory">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    <div class="memory-text">${escapeHtml(memory.text)}</div>
                    ${memory.has_audio ? '<div class="audio-indicator"><i class="fas fa-microphone"></i> Voice recording</div>' : ''}
                    <div class="memory-footer">
                        <span class="memory-date">
                            <i class="fas fa-calendar"></i> ${memory.memory_date || 'No specific date'}
                        </span>
                        <button onclick="addComment(${memory.id})" class="love-note-btn" title="Share your memory of this event">
                            <i class="fas fa-link"></i> Link Your Memory
                        </button>
                        <button onclick="browseAllPhotos(${memory.id})" class="btn btn-secondary" title="Browse all photos">
                            <i class="fas fa-images"></i> Browse Photos
                        </button>
                        <button onclick="suggestPhotos(${memory.id})" class="btn btn-secondary" title="Get AI suggestions">
                            <i class="fas fa-magic"></i> Suggest Photos
                        </button>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading memories:', error);
        document.getElementById('timeline-content').innerHTML = 
            '<div class="error"><i class="fas fa-exclamation-triangle"></i><p>Error loading memories. Please try again.</p></div>';
    }
}

function searchTimeline() {
    const searchTerm = document.getElementById('timeline-search').value.trim();
    loadMemoriesWithSearch(searchTerm);
}

function clearTimelineSearch() {
    document.getElementById('timeline-search').value = '';
    loadMemories();
}

async function loadMemoriesWithSearch(searchTerm) {
    try {
        const response = await fetch('/api/memories/get');
        const data = await response.json();
        const memories = data.memories || [];
        
        const container = document.getElementById('timeline-content');
        
        if (!memories || memories.length === 0) {
            container.innerHTML = '<div class="empty-state">No memories found.</div>';
            return;
        }
        
        // Filter memories by search term
        let filteredMemories = memories;
        if (searchTerm) {
            const searchLower = searchTerm.toLowerCase();
            filteredMemories = memories.filter(memory => 
                memory.text.toLowerCase().includes(searchLower) ||
                (memory.category && memory.category.toLowerCase().includes(searchLower)) ||
                (memory.year && memory.year.toString().includes(searchTerm))
            );
        }
        
        if (filteredMemories.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-search-minus fa-3x"></i>
                    <h3>No Memories Found</h3>
                    <p>No memories match your search for "${searchTerm}".</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        filteredMemories.forEach(memory => {
            let displayText = memory.text;
            if (searchTerm) {
                // Highlight search term
                const regex = new RegExp(`(${searchTerm})`, 'gi');
                displayText = memory.text.replace(regex, '<mark>$1</mark>');
            }
            
            html += `
                <div class="memory-card" data-id="${memory.id}">
                    <div class="memory-header">
                        <div>
                            <span class="memory-year">${memory.year || 'Unknown year'}</span>
                            <span class="memory-category">${memory.category || 'memory'}</span>
                        </div>
                        <div class="memory-actions">
                            <button onclick="editMemory(${memory.id})" class="btn-icon" title="Edit this memory">
                                <i class="fas fa-pencil-alt"></i>
                            </button>
                            <button onclick="deleteMemory(${memory.id})" class="delete-btn" title="Delete this memory">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    <div class="memory-text">${displayText}</div>
                    ${memory.has_audio ? '<div class="audio-indicator"><i class="fas fa-microphone"></i> Voice recording</div>' : ''}
                    <div class="memory-footer">
                        <span class="memory-date">
                            <i class="fas fa-calendar"></i> ${memory.memory_date || 'No specific date'}
                        </span>
                        <button onclick="addComment(${memory.id})" class="love-note-btn" title="Share your memory of this event">
                            <i class="fas fa-link"></i> Link Your Memory
                        </button>
                        <button onclick="browseAllPhotos(${memory.id})" class="btn btn-secondary" title="Browse all photos">
                            <i class="fas fa-images"></i> Browse Photos
                        </button>
                        <button onclick="suggestPhotos(${memory.id})" class="btn btn-secondary" title="Get AI suggestions">
                            <i class="fas fa-magic"></i> Suggest Photos
                        </button>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error searching memories:', error);
        document.getElementById('timeline-content').innerHTML = 
            '<div class="error">Error searching memories.</div>';
    }
}

async function deleteMemory(memoryId) {
    // Confirmation dialog
    const confirmed = confirm(
        "Are you sure you want to delete this memory?\n\n" +
        "This will permanently delete:\n" +
        "• The memory text\n" +
        "• Any voice recording\n" +
        "• All love notes\n\n" +
        "This cannot be undone!"
    );
    
    if (!confirmed) {
        return; // User cancelled
    }
    
    try {
        const response = await fetch(`/api/memories/delete/${memoryId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Remove the memory card from the page with fade out animation
            const memoryCard = document.querySelector(`[data-id="${memoryId}"]`);
            if (memoryCard) {
                memoryCard.style.transition = 'opacity 0.3s ease-out';
                memoryCard.style.opacity = '0';
                setTimeout(() => {
                    memoryCard.remove();
                    
                    // Check if timeline is now empty
                    const container = document.getElementById('timeline-content');
                    if (container.children.length === 0) {
                        loadMemories(); // Reload to show "No memories" message
                    }
                }, 300);
            }
            
            // Show success message (optional)
            console.log('Memory deleted successfully');
        } else {
            alert('Error deleting memory: ' + data.message);
        }
    } catch (error) {
        console.error('Error deleting memory:', error);
        alert('Error deleting memory. Please try again.');
    }
}

async function editMemory(memoryId) {
    // Load the memory into the capture form
    fetch(`/api/memories/${memoryId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const memory = data.memory;
                
                // Switch to capture tab
                showTab('capture');
                
                // Populate form
                document.getElementById('memory-text').value = memory.text;
                document.getElementById('memory-date').value = memory.memory_date || '';
                
                // Store the memory ID for updating
                document.getElementById('memory-text').dataset.editingId = memoryId;
                
                // Change save button text
                const saveBtn = document.querySelector('#capture button[onclick="saveMemory()"]');
                if (saveBtn) {
                    saveBtn.innerHTML = '<i class="fas fa-save"></i> Update Memory';
                }
                
                // Add notice
                const form = document.querySelector('#capture .form-group');
                if (form && !document.querySelector('.edit-notice')) {
                    const notice = document.createElement('div');
                    notice.className = 'edit-notice';
                    notice.innerHTML = `
                        <i class="fas fa-info-circle"></i> 
                        Editing existing memory. 
                        <button onclick="cancelEdit()" class="btn-link">Cancel</button>
                    `;
                    form.insertBefore(notice, form.firstChild);
                }
                
            } else {
                alert('Error loading memory: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error loading memory:', error);
            alert('Failed to load memory for editing');
        });
}

function cancelEdit() {
    // Clear the form
    document.getElementById('memory-text').value = '';
    document.getElementById('memory-date').value = '';
    delete document.getElementById('memory-text').dataset.editingId;
    
    // Reset save button
    const saveBtn = document.querySelector('#capture button[onclick="saveMemory()"]');
    if (saveBtn) {
        saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Memory';
    }
    
    // Remove notice
    const notice = document.querySelector('.edit-notice');
    if (notice) notice.remove();
}

async function suggestPhotos(memoryId) {
    try {
        const response = await fetch(`/api/memories/${memoryId}/suggest-photos`);
        const data = await response.json();
        
        if (data.status === 'success' && data.suggestions && data.suggestions.length > 0) {
            // Show suggestions modal
            showPhotoSuggestions(memoryId, data.suggestions);
        } else {
            alert('No matching photos found for this memory.');
        }
    } catch (error) {
        console.error('Error getting photo suggestions:', error);
        alert('Error loading photo suggestions. Please try again.');
    }
}

function showPhotoSuggestions(memoryId, suggestions) {
    // Create modal HTML
    let html = `
        <div class="modal-overlay" onclick="closePhotoSuggestions()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <h3>Suggested Photos for This Memory</h3>
                <p>Click on photos to link them to this memory:</p>
                <div class="photo-suggestions-grid">
    `;
    
    suggestions.forEach(photo => {
        html += `
            <div class="suggestion-card">
                <img src="/uploads/${photo.filename}" alt="${photo.title || photo.original_filename}">
                <p><strong>${photo.title || photo.original_filename}</strong></p>
                <p class="match-reason">${photo.match_reason}</p>
                <button onclick="acceptPhotoSuggestion(${memoryId}, ${photo.id})" class="btn-primary">
                    <i class="fas fa-link"></i> Link This Photo
                </button>
            </div>
        `;
    });
    
    html += `
                </div>
                <button onclick="closePhotoSuggestions()" class="btn-secondary">
                    <i class="fas fa-times"></i> Close
                </button>
            </div>
        </div>
    `;
    
    // Inject modal
    const modalDiv = document.createElement('div');
    modalDiv.id = 'photo-suggestions-modal';
    modalDiv.innerHTML = html;
    document.body.appendChild(modalDiv);
}

function closePhotoSuggestions() {
    const modal = document.getElementById('photo-suggestions-modal');
    if (modal) modal.remove();
}

async function acceptPhotoSuggestion(memoryId, photoId) {
    try {
        const response = await fetch(`/api/memories/${memoryId}/accept-suggestion`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({photo_id: photoId})
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            alert('Photo linked successfully!');
            closePhotoSuggestions();
            closePhotoBrowser();
            loadMemories(); // Refresh timeline
        } else {
            alert('Error linking photo: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error accepting suggestion:', error);
        alert('Error linking photo. Please try again.');
    }
}

// Function to browse all photos manually
async function browseAllPhotos(memoryId) {
    try {
        const response = await fetch(`/api/memories/${memoryId}/browse-photos`);
        const data = await response.json();
        
        if (data.status === 'success' && data.photos && data.photos.length > 0) {
            showPhotoBrowser(memoryId, data.photos);
        } else {
            alert('No photos available to link.');
        }
    } catch (error) {
        console.error('Error loading photos:', error);
        alert('Error loading photos. Please try again.');
    }
}

// Show photo browser modal (similar to suggestions but without scores)
function showPhotoBrowser(memoryId, photos) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.id = 'photo-browser-modal';
    
    const modal = document.createElement('div');
    modal.className = 'modal-content';
    
    modal.innerHTML = `
        <h3>Select Photos to Link</h3>
        <p>Click on any photo to link it to this memory:</p>
        <div class="photo-suggestions-grid">
            ${photos.map(photo => `
                <div class="suggestion-card">
                    <img src="/uploads/${photo.filename}" alt="${photo.title}">
                    <p><strong>${photo.title}</strong></p>
                    ${photo.year !== 'Unknown' ? `<p>Year: ${photo.year}</p>` : ''}
                    ${photo.description ? `<p class="match-reason">${photo.description}</p>` : ''}
                    <button class="btn btn-primary" onclick="acceptPhotoSuggestion(${memoryId}, ${photo.id})">
                        <i class="fas fa-link"></i> Link This Photo
                    </button>
                </div>
            `).join('')}
        </div>
        <button class="btn btn-secondary" onclick="closePhotoBrowser()">
            <i class="fas fa-times"></i> Close
        </button>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closePhotoBrowser();
        }
    });
}

function closePhotoBrowser() {
    const modal = document.getElementById('photo-browser-modal');
    if (modal) {
        modal.remove();
    }
}

// Make functions globally available
window.editMemory = editMemory;
window.cancelEdit = cancelEdit;
window.loadMemories = loadMemories;
window.loadTimeline = loadMemories;
window.deleteMemory = deleteMemory;
window.suggestPhotos = suggestPhotos;
window.acceptPhotoSuggestion = acceptPhotoSuggestion;
window.closePhotoSuggestions = closePhotoSuggestions;
window.browseAllPhotos = browseAllPhotos;
window.closePhotoBrowser = closePhotoBrowser;
