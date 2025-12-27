// timeline.js - Timeline functions with DELETE functionality

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
                        <button onclick="deleteMemory(${memory.id})" class="delete-btn" title="Delete this memory">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                    <div class="memory-text">${escapeHtml(memory.text)}</div>
                    ${memory.has_audio ? '<div class="audio-indicator"><i class="fas fa-microphone"></i> Voice recording</div>' : ''}
                    <div class="memory-footer">
                        <span class="memory-date">
                            <i class="fas fa-calendar"></i> ${memory.memory_date || 'No specific date'}
                        </span>
                        <button onclick="addComment(${memory.id})" class="love-note-btn">
                            <i class="fas fa-heart"></i> Add Love Note
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
                        <button onclick="deleteMemory(${memory.id})" class="delete-btn" title="Delete this memory">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                    <div class="memory-text">${displayText}</div>
                    ${memory.has_audio ? '<div class="audio-indicator"><i class="fas fa-microphone"></i> Voice recording</div>' : ''}
                    <div class="memory-footer">
                        <span class="memory-date">
                            <i class="fas fa-calendar"></i> ${memory.memory_date || 'No specific date'}
                        </span>
                        <button onclick="addComment(${memory.id})" class="love-note-btn">
                            <i class="fas fa-heart"></i> Add Love Note
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
            
            // Show success message
            alert('Memory deleted successfully! 🗑️');
        } else {
            alert('Error deleting memory: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error deleting memory:', error);
        alert('Error deleting memory. Please try again.');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions available globally
window.loadMemories = loadMemories;
window.loadTimeline = loadMemories;
window.deleteMemory = deleteMemory;
