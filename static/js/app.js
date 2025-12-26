// static/js/app.js - Main app initialization
document.addEventListener('DOMContentLoaded', async function() {
    console.log('The Circle - Family Memory App Starting...');
    
    // Check server health
    try {
        const response = await fetch('/api/health');
        if (!response.ok) throw new Error('Server not responding');
        console.log('✓ Server is healthy');
    } catch (error) {
        console.error('✗ Server error:', error);
        alert('Server is not responding. Please make sure the Python server is running.');
        return;
    }
    
    // Check if profile exists
    const hasProfile = await checkProfile();
    
    if (!hasProfile) {
        showProfileSetup();
    } else {
        showMainInterface();
    }
    
    // Load initial data
    if (document.getElementById('timeline').classList.contains('active')) {
        loadMemories();
    }
});

async function checkProfile() {
    try {
        const response = await fetch('/api/profile/get');
        const data = await response.json();
        return data.exists;
    } catch {
        return false;
    }
}

function showProfileSetup() {
    document.getElementById('profile-setup').style.display = 'block';
    document.querySelector('.tab-container').style.display = 'none';
}

function showMainInterface() {
    document.getElementById('profile-setup').style.display = 'none';
    document.querySelector('.tab-container').style.display = 'flex';
    document.getElementById('capture').classList.add('active');
}

// Tab management
// Tab management
window.showTab = function(tabName, event) {
    // If called from onclick, event is passed
    if (!event) {
        event = window.event;
    }
    
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active from all tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    
    // Activate the clicked tab button if event exists
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    } else {
        // Find and activate the tab button
        document.querySelectorAll('.tab').forEach(tab => {
            if (tab.onclick && tab.onclick.toString().includes(`'${tabName}'`)) {
                tab.classList.add('active');
            }
        });
    }
    
    // Load data for specific tabs
    switch(tabName) {
        case 'timeline':
            if (typeof loadMemories === 'function') {
                loadMemories();
            }
            break;
        case 'media':
            if (window.mediaManager && typeof window.mediaManager.loadMediaGallery === 'function') {
                setTimeout(() => window.mediaManager.loadMediaGallery(), 100);
            }
            break;
        case 'comments':
            if (typeof loadComments === 'function') {
                loadComments();
            }
            break;
        // Note: Removed 'search' case since loadSearch doesn't exist
    }
};
// Initialize media manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // ... existing code ...
    
    // Initialize media manager if it exists
    if (typeof MediaManager !== 'undefined' && !window.mediaManager) {
        window.mediaManager = new MediaManager();
    }
});