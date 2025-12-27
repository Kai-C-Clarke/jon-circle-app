// Add these functions to timeline.js

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

// Update the memory card HTML to include both buttons
// This replaces the single "Suggest Photos" button with two buttons side by side

// In the createMemoryCard function, replace the suggest photos button section with:
/*
<div class="memory-actions">
    <button class="btn btn-secondary" onclick="browseAllPhotos(${memory.id})" title="Browse all photos">
        <i class="fas fa-images"></i> Browse Photos
    </button>
    <button class="btn btn-secondary" onclick="suggestPhotos(${memory.id})" title="Get AI suggestions">
        <i class="fas fa-magic"></i> Suggest Photos
    </button>
</div>
*/
