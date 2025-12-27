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

async function saveMemory() {
    const text = document.getElementById('memory-text').value.trim();
    const dateInput = document.getElementById('memory-date').value.trim();
    
    if (!text) {
        alert('Please write something before saving.');
        return;
    }
    
    try {
        const response = await fetch('/api/memories/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                text: text,
                date_input: dateInput 
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Clear form
            document.getElementById('memory-text').value = '';
            document.getElementById('memory-date').value = '';
            
            // Show success message
            let message = `Memory saved successfully!`;
            if (data.category) message += `\nCategory: ${data.category}`;
            if (data.year) message += `\nYear: ${data.year}`;
            
            alert(message);
            
            // Refresh timeline if active
            if (document.getElementById('timeline').classList.contains('active')) {
                loadMemories();
            }
        } else {
            alert('Error saving memory: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to save memory. Please make sure the server is running.');
    }
}