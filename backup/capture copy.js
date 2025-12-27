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
    const text = document.getElementById('memory-text').value.trim();
    const date = document.getElementById('memory-date').value.trim();
    
    // Get audio filename if recording was made
    const audioFilename = document.getElementById('audio-filename-hidden').value;
    
    if (!text) {
        alert('Please write or record your memory first');
        return;
    }
    
    try {
        const response = await fetch('/api/memories/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                memory_date: date,
                audio_filename: audioFilename
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            alert('Memory saved to your family timeline! 💝');
            
            // Clear form
            document.getElementById('memory-text').value = '';
            document.getElementById('memory-date').value = '';
            document.getElementById('audio-filename-hidden').value = '';
            
            // Hide success message if shown
            const successMsg = document.getElementById('recording-success');
            if (successMsg) {
                successMsg.style.display = 'none';
            }
            
            // Try to reload timeline if function exists
            if (typeof loadTimeline === 'function') {
                loadTimeline();
            }
        } else {
            alert('Error saving memory: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error saving memory:', error);
        alert('Error saving memory. Please try again.');
    }
}
