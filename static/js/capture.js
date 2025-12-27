// capture.js - Memory capture functions
function suggestPrompt(type) {
    const textarea = document.getElementById('memory-text');
    const dateInput = document.getElementById('memory-date');
    
    const prompts = {
        childhood: {
            text: "Describe the house you grew up in. What did your room look like? What smells and sounds do you remember from your childhood?",
            date: "1950-1960"
        },
        'first-job': {
            text: "Tell me about your first job. Who were your coworkers? What did you learn from that experience?",
            date: "1973"
        },
        family: {
            text: "Share a favorite family story that's been passed down through generations. Who told it to you first?",
            date: ""
        },
        travel: {
            text: "Recall a memorable trip you took. Where did you go? Who were you with? What made it special?",
            date: "1982"
        }
    };
    
    const prompt = prompts[type];
    if (prompt) {
        textarea.value = prompt.text;
        dateInput.value = prompt.date;
        textarea.focus();
    }
}

// UPDATE THIS FUNCTION IN capture.js

async function saveMemory() {
    const textArea = document.getElementById('memory-text');
    const text = textArea.value.trim();
    const date = document.getElementById('memory-date').value.trim();
    
    if (!text) {
        alert('Please write a memory before saving');
        return;
    }
    
    // Check if we're editing or creating
    const editingId = textArea.dataset.editingId;
    const isEditing = editingId !== undefined && editingId !== null;
    
    try {
        let response;
        
        if (isEditing) {
            // UPDATE existing memory
            response = await fetch(`/api/memories/${editingId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text, date: date})
            });
        } else {
            // CREATE new memory
            response = await fetch('/api/memories/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text, date: date})
            });
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            alert(isEditing ? 'Memory updated!' : 'Memory saved!');
            
            // Clear the form
            textArea.value = '';
            document.getElementById('memory-date').value = '';
            delete textArea.dataset.editingId;
            
            // Reset save button
            const saveBtn = document.querySelector('#capture button[onclick="saveMemory()"]');
            if (saveBtn) {
                saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Memory';
            }
            
            // Remove edit notice
            const notice = document.querySelector('.edit-notice');
            if (notice) notice.remove();
            
            // Reload timeline
            if (typeof loadMemories === 'function') {
                loadMemories();
            }
            
            // Switch to timeline
            showTab('timeline');
        } else {
            alert('Error: ' + data.message);
        }
        
    } catch (error) {
        console.error('Error saving memory:', error);
        alert('Failed to save memory. Please try again.');
    }
}
