// voice_recorder.js - Voice recording and transcription for family stories

let mediaRecorder = null;
let audioChunks = [];
let recognition = null;
let isRecording = false;
let recordingStartTime = null;
let timerInterval = null;

// Initialize speech recognition if available
function initSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-GB'; // British English - change to en-US if needed
        
        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Update the memory text field with transcription
            const memoryText = document.getElementById('memory-text');
            const currentText = memoryText.value;
            
            if (finalTranscript) {
                // Append final transcription
                memoryText.value = currentText + finalTranscript;
            }
            
            // Show interim results in the transcription preview
            const preview = document.getElementById('transcription-preview');
            if (preview) {
                preview.textContent = interimTranscript || 'Listening...';
            }
        };
        
        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (event.error === 'not-allowed') {
                alert('Microphone access denied. Please allow microphone access to record stories.');
            }
        };
        
        return true;
    }
    return false;
}

// Start voice recording
async function startVoiceRecording() {
    try {
        // Request microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Initialize MediaRecorder for audio capture
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            // Create audio blob
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            
            // Save audio file
            await saveAudioRecording(audioBlob);
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };
        
        // Start recording
        mediaRecorder.start();
        isRecording = true;
        recordingStartTime = Date.now();
        
        // Start speech recognition if available
        if (recognition) {
            recognition.start();
        }
        
        // Update UI
        updateRecordingUI(true);
        
        // Start timer
        startRecordingTimer();
        
    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Could not access microphone. Please check your browser permissions.');
    }
}

// Stop voice recording
function stopVoiceRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        // Stop speech recognition
        if (recognition) {
            recognition.stop();
        }
        
        // Stop timer
        stopRecordingTimer();
        
        // Update UI
        updateRecordingUI(false);
    }
}

// Pause/resume recording
function togglePauseRecording() {
    if (!mediaRecorder || !isRecording) return;
    
    if (mediaRecorder.state === 'recording') {
        mediaRecorder.pause();
        if (recognition) recognition.stop();
        document.getElementById('pause-btn').innerHTML = '<i class="fas fa-play"></i> Resume';
    } else if (mediaRecorder.state === 'paused') {
        mediaRecorder.resume();
        if (recognition) recognition.start();
        document.getElementById('pause-btn').innerHTML = '<i class="fas fa-pause"></i> Pause';
    }
}

// Save audio recording
async function saveAudioRecording(audioBlob) {
    try {
        const formData = new FormData();
        const filename = `recording_${Date.now()}.webm`;
        formData.append('audio', audioBlob, filename);
        
        const response = await fetch('/api/audio/save', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            console.log('Audio saved:', data.filename);
            
            // Store filename for later association with memory
            const audioFileInput = document.getElementById('audio-filename-hidden');
            if (audioFileInput) {
                audioFileInput.value = data.filename;
            }
            
            // Show success message
            showRecordingSuccess(data.duration);
        } else {
            alert('Failed to save audio recording');
        }
    } catch (error) {
        console.error('Error saving audio:', error);
        alert('Error saving audio recording');
    }
}

// Update UI during recording
function updateRecordingUI(recording) {
    const recordBtn = document.getElementById('record-voice-btn');
    const recordingControls = document.getElementById('recording-controls');
    const transcriptionPreview = document.getElementById('transcription-preview');
    
    if (recording) {
        recordBtn.style.display = 'none';
        recordingControls.style.display = 'flex';
        transcriptionPreview.style.display = 'block';
    } else {
        recordBtn.style.display = 'block';
        recordingControls.style.display = 'none';
        transcriptionPreview.style.display = 'none';
    }
}

// Recording timer
function startRecordingTimer() {
    const timerDisplay = document.getElementById('recording-timer');
    
    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        timerDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);
}

function stopRecordingTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

// Show success message
function showRecordingSuccess(duration) {
    const successMsg = document.getElementById('recording-success');
    if (successMsg) {
        const durationText = duration ? ` (${duration}s)` : '';
        successMsg.innerHTML = `<i class="fas fa-check-circle"></i> Recording saved${durationText}! Your voice will be preserved with this memory.`;
        successMsg.style.display = 'block';
        
        setTimeout(() => {
            successMsg.style.display = 'none';
        }, 5000);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Check if speech recognition is available
    const speechAvailable = initSpeechRecognition();
    
    // Show/hide features based on browser support
    if (!speechAvailable) {
        console.log('Speech recognition not available in this browser');
        // Could show a message to user
    }
    
    // Check if audio recording is available
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.log('Audio recording not available in this browser');
        const recordBtn = document.getElementById('record-voice-btn');
        if (recordBtn) {
            recordBtn.disabled = true;
            recordBtn.title = 'Voice recording not supported in this browser';
        }
    }
});

// Export functions for global access
window.startVoiceRecording = startVoiceRecording;
window.stopVoiceRecording = stopVoiceRecording;
window.togglePauseRecording = togglePauseRecording;
