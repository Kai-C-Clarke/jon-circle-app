// media.js - Handle media upload and gallery (FIXED VERSION)

class MediaManager {
    constructor() {
        this.uploadForm = document.getElementById('media-upload-form');
        this.dropZone = document.getElementById('media-drop-zone');
        this.fileInput = document.getElementById('media-file-input');
        this.uploadBtn = document.getElementById('media-upload-btn');
        this.mediaGallery = document.getElementById('media-gallery');
        this.previewContainer = document.getElementById('media-preview');
        
        this.selectedFiles = [];
        this.uploadInProgress = false;
        this.isGalleryLoading = false;  // NEW: Track loading state
        this.galleryLoadTimeout = null; // NEW: Debounce timeout
        
        this.initializeEventListeners();
        this.loadMediaGallery();
        
        // Initialize lightbox
        this.initLightbox();
    }
    
    initializeEventListeners() {
        // File input change
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
        
        // Upload button
        if (this.uploadBtn) {
            this.uploadBtn.addEventListener('click', () => this.fileInput?.click());
        }
        
        // Drag and drop
        if (this.dropZone) {
            this.dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.dropZone.classList.add('dragover');
            });
            
            this.dropZone.addEventListener('dragleave', () => {
                this.dropZone.classList.remove('dragover');
            });
            
            this.dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                this.dropZone.classList.remove('dragover');
                this.handleFileSelect({ target: { files: e.dataTransfer.files } });
            });
        }
        
        // Upload form submit
        if (this.uploadForm) {
            // Remove any existing listener first
            this.uploadForm.removeEventListener('submit', this.handleUploadBound);
            this.handleUploadBound = this.handleUpload.bind(this);
            this.uploadForm.addEventListener('submit', this.handleUploadBound);
        }
    }
    
    handleFileSelect(event) {
        const files = Array.from(event.target.files || []);
        
        // Filter by allowed file types
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 
                              'application/pdf', 'audio/mpeg', 'audio/wav', 
                              'video/mp4', 'video/quicktime'];
        
        const validFiles = files.filter(file => allowedTypes.includes(file.type) || 
            file.name.toLowerCase().match(/\.(jpg|jpeg|png|gif|webp|pdf|mp3|wav|mp4|mov|avi)$/));
        
        if (validFiles.length === 0) {
            this.showMessage('No valid files selected. Please select images, PDFs, audio, or video files.', 'error');
            return;
        }
        
        // Check file sizes
        const maxSize = 50 * 1024 * 1024;
        const oversizedFiles = validFiles.filter(file => file.size > maxSize);
        
        if (oversizedFiles.length > 0) {
            this.showMessage(`Some files exceed 50MB limit: ${oversizedFiles.map(f => f.name).join(', ')}`, 'error');
            this.selectedFiles = validFiles.filter(file => file.size <= maxSize);
        } else {
            this.selectedFiles = validFiles;
        }
        
        if (this.selectedFiles.length > 0) {
            this.showPreview();
        }
        
        if (this.fileInput) {
            this.fileInput.value = '';
        }
    }
    
    showPreview() {
        if (!this.previewContainer) return;
        
        if (this.selectedFiles.length === 0) {
            this.previewContainer.innerHTML = '';
            if (this.uploadForm) {
                this.uploadForm.style.display = 'none';
            }
            return;
        }
        
        this.previewContainer.innerHTML = '';
        
        this.selectedFiles.forEach((file, index) => {
            const previewDiv = document.createElement('div');
            previewDiv.className = 'media-preview-item';
            previewDiv.dataset.index = index;
            
            let previewHTML = '';
            let fileType = 'document';
            
            if (file.type.startsWith('image/')) {
                fileType = 'image';
                const url = URL.createObjectURL(file);
                previewHTML = `
                    <div class="preview-image">
                        <img src="${url}" alt="${file.name}" loading="lazy">
                        <button type="button" class="remove-file" data-index="${index}">×</button>
                    </div>
                    <div class="preview-info">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                        <div class="file-type">Image</div>
                    </div>
                `;
                // Clean up object URL when element is removed
                previewDiv.addEventListener('remove', () => URL.revokeObjectURL(url));
            } else if (file.type.startsWith('audio/')) {
                fileType = 'audio';
                previewHTML = `
                    <div class="preview-icon audio">
                        <i class="fas fa-music"></i>
                        <button type="button" class="remove-file" data-index="${index}">×</button>
                    </div>
                    <div class="preview-info">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                        <div class="file-type">Audio</div>
                    </div>
                `;
            } else if (file.type.startsWith('video/')) {
                fileType = 'video';
                previewHTML = `
                    <div class="preview-icon video">
                        <i class="fas fa-video"></i>
                        <button type="button" class="remove-file" data-index="${index}">×</button>
                    </div>
                    <div class="preview-info">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                        <div class="file-type">Video</div>
                    </div>
                `;
            } else if (file.type === 'application/pdf') {
                fileType = 'pdf';
                previewHTML = `
                    <div class="preview-icon pdf">
                        <i class="fas fa-file-pdf"></i>
                        <button type="button" class="remove-file" data-index="${index}">×</button>
                    </div>
                    <div class="preview-info">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                        <div class="file-type">PDF</div>
                    </div>
                `;
            } else {
                previewHTML = `
                    <div class="preview-icon document">
                        <i class="fas fa-file"></i>
                        <button type="button" class="remove-file" data-index="${index}">×</button>
                    </div>
                    <div class="preview-info">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                        <div class="file-type">Document</div>
                    </div>
                `;
            }
            
            previewDiv.className = `media-preview-item ${fileType}`;
            previewDiv.innerHTML = previewHTML;
            this.previewContainer.appendChild(previewDiv);
            
            const removeBtn = previewDiv.querySelector('.remove-file');
            if (removeBtn) {
                removeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const index = parseInt(e.target.dataset.index || e.target.closest('.remove-file').dataset.index);
                    this.removeFile(index);
                });
            }
        });
        
        if (this.uploadForm) {
            this.uploadForm.style.display = 'block';
        }
    }
    
    removeFile(index) {
        const previewItem = this.previewContainer.querySelector(`[data-index="${index}"]`);
        if (previewItem && previewItem.classList.contains('image')) {
            const img = previewItem.querySelector('img');
            if (img && img.src.startsWith('blob:')) {
                URL.revokeObjectURL(img.src);
            }
        }
        
        this.selectedFiles.splice(index, 1);
        
        const remainingItems = this.previewContainer.querySelectorAll('.media-preview-item');
        remainingItems.forEach((item, newIndex) => {
            item.dataset.index = newIndex;
            const removeBtn = item.querySelector('.remove-file');
            if (removeBtn) {
                removeBtn.dataset.index = newIndex;
            }
        });
        
        this.showPreview();
    }
    
    formatFileSize(bytes) {
        if (bytes === null || bytes === undefined || bytes === '') {
            return 'Unknown size';
        }
        
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    async handleUpload(event) {
        event.preventDefault();
        
        if (this.selectedFiles.length === 0) {
            this.showMessage('Please select files to upload', 'error');
            return;
        }
        
        if (this.uploadInProgress) {
            console.log('Upload already in progress, skipping...');
            return;
        }
        
        this.uploadInProgress = true;
        const originalBtnText = this.uploadBtn.innerHTML;
        this.uploadBtn.disabled = true;
        this.uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
        
        const title = document.getElementById('media-title')?.value || '';
        const description = document.getElementById('media-description')?.value || '';
        const memoryDate = document.getElementById('media-date')?.value || '';
        const year = document.getElementById('media-year')?.value || '';
        const people = document.getElementById('media-people')?.value || '';
        
        let successCount = 0;
        let errorCount = 0;
        const errors = [];
        
        console.log(`Starting upload of ${this.selectedFiles.length} files`);
        
        for (const file of this.selectedFiles) {
            try {
                const formData = new FormData();
                formData.append('media', file);
                formData.append('title', title || file.name);
                formData.append('description', description);
                formData.append('memory_date', memoryDate);
                formData.append('year', year);
                formData.append('people', people);
                formData.append('original_filename', file.name);
                formData.append('file_size', file.size);
                
                console.log(`Uploading: ${file.name}`);
                const response = await fetch('/api/media/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok && result.status === 'success') {
                    console.log(`Success: ${file.name}`);
                    successCount++;
                } else {
                    console.error(`Failed: ${file.name} - ${result.message || 'Upload failed'}`);
                    errorCount++;
                    errors.push(`${file.name}: ${result.message || 'Upload failed'}`);
                }
            } catch (error) {
                console.error(`Error: ${file.name} - ${error.message}`);
                errorCount++;
                errors.push(`${file.name}: ${error.message}`);
            }
        }
        
        this.uploadInProgress = false;
        this.uploadBtn.disabled = false;
        this.uploadBtn.innerHTML = originalBtnText;
        
        if (successCount > 0) {
            const message = `Successfully uploaded ${successCount} file(s)`;
            console.log(message);
            this.selectedFiles = [];
            this.showPreview();
            
            // Use debounced gallery refresh instead of direct call
            this.debouncedGalleryRefresh();
            
            if (this.uploadForm) {
                this.uploadForm.reset();
                this.uploadForm.style.display = 'none';
            }
            
            this.showMessage(message, 'success');
        }
        
        if (errorCount > 0) {
            const errorMessage = `Failed to upload ${errorCount} file(s): ${errors.join('; ')}`;
            console.error(errorMessage);
            this.showMessage(errorMessage, 'error');
        }
    }
    
    // NEW: Debounced gallery refresh
    debouncedGalleryRefresh() {
        if (this.galleryLoadTimeout) {
            clearTimeout(this.galleryLoadTimeout);
        }
        
        // Wait 500ms before refreshing to avoid rapid consecutive calls
        this.galleryLoadTimeout = setTimeout(() => {
            this.loadMediaGallery();
            this.galleryLoadTimeout = null;
        }, 500);
    }
    
    async loadMediaGallery() {
        // Prevent multiple simultaneous loads
        if (this.isGalleryLoading) {
            console.log('Gallery already loading, skipping...');
            return;
        }
        
        console.log('Loading media gallery...');
        
        if (!this.mediaGallery) {
            console.error('mediaGallery element not found!');
            return;
        }
        
        this.isGalleryLoading = true;
        
        try {
            this.mediaGallery.innerHTML = `
                <div class="loading-gallery">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Loading media...</p>
                </div>
            `;
            
            const response = await fetch('/api/media/all');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const mediaItems = await response.json();
            console.log(`Loaded ${mediaItems.length} media items`);
            this.renderMediaGallery(mediaItems);
        } catch (error) {
            console.error('Error loading media gallery:', error);
            this.mediaGallery.innerHTML = `
                <div class="error-gallery">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Failed to load media gallery</p>
                    <button onclick="window.mediaManager.loadMediaGallery()" class="retry-btn">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                </div>
            `;
        } finally {
            this.isGalleryLoading = false;
        }
    }
    
    renderMediaGallery(mediaItems) {
        if (!this.mediaGallery) return;
        
        if (!mediaItems || mediaItems.length === 0) {
            this.mediaGallery.innerHTML = `
                <div class="empty-gallery">
                    <i class="fas fa-images"></i>
                    <p>No media uploaded yet</p>
                    <p>Drag and drop files or click upload to add media</p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="media-grid">';
        
        mediaItems.forEach(item => {
            let mediaElement = '';
            const fileType = item.file_type?.split('/')[0] || item.file_type || 'document';
            
            if (fileType.startsWith('image')) {
                mediaElement = `
                    <div class="media-item image" data-id="${item.id}">
                        <div class="media-thumbnail">
                            <img src="/uploads/${item.filename}" alt="${item.title || item.original_filename}" 
                                 loading="lazy" data-url="/uploads/${item.filename}">
                            <div class="media-overlay">
                                <button class="media-view" title="View full size">
                                    <i class="fas fa-expand"></i>
                                </button>
                                <button class="media-edit" data-id="${item.id}" title="Edit details">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="media-delete" data-id="${item.id}" title="Delete">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                        <div class="media-info">
                            <div class="editable-title">
                                <h4 class="title-display">${item.title || item.original_filename}</h4>
                                <input type="text" class="title-edit" value="${item.title || item.original_filename}" 
                                       style="display: none;" data-original="${item.title || item.original_filename}">
                                <button class="save-title-btn" data-id="${item.id}" style="display: none;">
                                    <i class="fas fa-check"></i>
                                </button>
                                <button class="cancel-title-btn" style="display: none;">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                            <div class="editable-description">
                                <p class="description-display">${item.description || 'No description'}</p>
                                <textarea class="description-edit" style="display: none;" 
                                          placeholder="Add a description...">${item.description || ''}</textarea>
                                <button class="save-description-btn" data-id="${item.id}" style="display: none;">
                                    <i class="fas fa-check"></i>
                                </button>
                                <button class="cancel-description-btn" style="display: none;">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                            <small>${this.formatFileSize(item.file_size)} • ${new Date(item.created_at).toLocaleDateString()}</small>
                        </div>
                    </div>
                `;
            } else if (fileType.startsWith('audio')) {
                mediaElement = `
                    <div class="media-item audio" data-id="${item.id}">
                        <div class="media-thumbnail">
                            <div class="audio-icon">
                                <i class="fas fa-music"></i>
                            </div>
                            <div class="media-overlay">
                                <a href="/uploads/${item.filename}" target="_blank" class="media-view" title="Play audio">
                                    <i class="fas fa-play"></i>
                                </a>
                                <button class="media-delete" data-id="${item.id}" title="Delete">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                        <div class="media-info">
                            <h4>${item.title || item.original_filename}</h4>
                            <p class="media-description">${item.description || 'No description'}</p>
                            <small>${this.formatFileSize(item.file_size)} • ${new Date(item.created_at).toLocaleDateString()}</small>
                        </div>
                    </div>
                `;
            } else if (fileType.startsWith('video')) {
                mediaElement = `
                    <div class="media-item video" data-id="${item.id}">
                        <div class="media-thumbnail">
                            <div class="video-icon">
                                <i class="fas fa-video"></i>
                            </div>
                            <div class="media-overlay">
                                <a href="/uploads/${item.filename}" target="_blank" class="media-view" title="Play video">
                                    <i class="fas fa-play"></i>
                                </a>
                                <button class="media-delete" data-id="${item.id}" title="Delete">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                        <div class="media-info">
                            <h4>${item.title || item.original_filename}</h4>
                            <p class="media-description">${item.description || 'No description'}</p>
                            <small>${this.formatFileSize(item.file_size)} • ${new Date(item.created_at).toLocaleDateString()}</small>
                        </div>
                    </div>
                `;
            } else if (item.file_type === 'application/pdf' || item.original_filename?.endsWith('.pdf')) {
                mediaElement = `
                    <div class="media-item pdf" data-id="${item.id}">
                        <div class="media-thumbnail">
                            <div class="pdf-icon">
                                <i class="fas fa-file-pdf"></i>
                            </div>
                            <div class="media-overlay">
                                <a href="/uploads/${item.filename}" target="_blank" class="media-view" title="View PDF">
                                    <i class="fas fa-eye"></i>
                                </a>
                                <button class="media-delete" data-id="${item.id}" title="Delete">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                        <div class="media-info">
                            <h4>${item.title || item.original_filename}</h4>
                            <p class="media-description">${item.description || 'No description'}</p>
                            <small>${this.formatFileSize(item.file_size)} • ${new Date(item.created_at).toLocaleDateString()}</small>
                        </div>
                    </div>
                `;
            } else {
                mediaElement = `
                    <div class="media-item document" data-id="${item.id}">
                        <div class="media-thumbnail">
                            <div class="document-icon">
                                <i class="fas fa-file"></i>
                            </div>
                            <div class="media-overlay">
                                <a href="/uploads/${item.filename}" target="_blank" class="media-view" title="Download">
                                    <i class="fas fa-download"></i>
                                </a>
                                <button class="media-delete" data-id="${item.id}" title="Delete">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                        <div class="media-info">
                            <h4>${item.title || item.original_filename}</h4>
                            <p class="media-description">${item.description || 'No description'}</p>
                            <small>${this.formatFileSize(item.file_size)} • ${new Date(item.created_at).toLocaleDateString()}</small>
                        </div>
                    </div>
                `;
            }
            
            html += mediaElement;
        });
        
        html += '</div>';
        this.mediaGallery.innerHTML = html;
        
        // Add event listeners
        this.attachGalleryEventListeners();
    }
    
    attachGalleryEventListeners() {
        // Delete buttons
        this.mediaGallery.querySelectorAll('.media-delete').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                const mediaId = btn.dataset.id;
                
                if (confirm('Are you sure you want to delete this media item? This cannot be undone.')) {
                    try {
                        const response = await fetch(`/api/media/delete/${mediaId}`, {
                            method: 'DELETE'
                        });
                        
                        if (response.ok) {
                            this.showMessage('Media deleted successfully', 'success');
                            this.debouncedGalleryRefresh();
                        } else {
                            const result = await response.json();
                            throw new Error(result.error || 'Delete failed');
                        }
                    } catch (error) {
                        console.error('Delete error:', error);
                        this.showMessage('Error deleting media: ' + error.message, 'error');
                    }
                }
            });
        });
        
        // View buttons for lightbox (images only)
        this.mediaGallery.querySelectorAll('.media-view').forEach(btn => {
            if (btn.closest('.image')) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const img = btn.closest('.media-thumbnail').querySelector('img');
                    if (img) {
                        this.openLightbox(img.src, img.alt);
                    }
                });
            }
        });
        
        // Edit buttons
        this.mediaGallery.querySelectorAll('.media-edit').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const mediaItem = btn.closest('.media-item');
                this.enableEditing(mediaItem);
            });
        });

        // Title editing (double-click)
        this.mediaGallery.querySelectorAll('.title-display').forEach(titleDisplay => {
            titleDisplay.addEventListener('dblclick', (e) => {
                const mediaItem = e.target.closest('.media-item');
                this.enableTitleEditing(mediaItem);
            });
        });

        // Description editing (double-click)
        this.mediaGallery.querySelectorAll('.description-display').forEach(descDisplay => {
            descDisplay.addEventListener('dblclick', (e) => {
                const mediaItem = e.target.closest('.media-item');
                this.enableDescriptionEditing(mediaItem);
            });
        });
    }
    
    // ============ EDITING METHODS ============
    
    enableEditing(mediaItem) {
        this.enableTitleEditing(mediaItem);
        this.enableDescriptionEditing(mediaItem);
    }
    
    enableTitleEditing(mediaItem) {
        const titleDisplay = mediaItem.querySelector('.title-display');
        const titleEdit = mediaItem.querySelector('.title-edit');
        const saveBtn = mediaItem.querySelector('.save-title-btn');
        const cancelBtn = mediaItem.querySelector('.cancel-title-btn');
        
        if (titleDisplay && titleEdit) {
            titleDisplay.style.display = 'none';
            titleEdit.style.display = 'block';
            saveBtn.style.display = 'inline-block';
            cancelBtn.style.display = 'inline-block';
            
            titleEdit.focus();
            titleEdit.select();
            
            // Save on Enter key
            titleEdit.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this.saveTitle(mediaItem);
                } else if (e.key === 'Escape') {
                    this.cancelTitleEditing(mediaItem);
                }
            });
            
            // Save button click
            saveBtn.onclick = () => this.saveTitle(mediaItem);
            
            // Cancel button click
            cancelBtn.onclick = () => this.cancelTitleEditing(mediaItem);
        }
    }
    
    enableDescriptionEditing(mediaItem) {
        const descDisplay = mediaItem.querySelector('.description-display');
        const descEdit = mediaItem.querySelector('.description-edit');
        const saveBtn = mediaItem.querySelector('.save-description-btn');
        const cancelBtn = mediaItem.querySelector('.cancel-description-btn');
        
        if (descDisplay && descEdit) {
            descDisplay.style.display = 'none';
            descEdit.style.display = 'block';
            saveBtn.style.display = 'inline-block';
            cancelBtn.style.display = 'inline-block';
            
            descEdit.focus();
            
            // Save button click
            saveBtn.onclick = () => this.saveDescription(mediaItem);
            
            // Cancel button click
            cancelBtn.onclick = () => this.cancelDescriptionEditing(mediaItem);
        }
    }
    
    cancelTitleEditing(mediaItem) {
        const titleDisplay = mediaItem.querySelector('.title-display');
        const titleEdit = mediaItem.querySelector('.title-edit');
        const saveBtn = mediaItem.querySelector('.save-title-btn');
        const cancelBtn = mediaItem.querySelector('.cancel-title-btn');
        
        const originalValue = titleEdit.dataset.original;
        titleEdit.value = originalValue;
        
        titleDisplay.style.display = 'block';
        titleEdit.style.display = 'none';
        saveBtn.style.display = 'none';
        cancelBtn.style.display = 'none';
    }
    
    cancelDescriptionEditing(mediaItem) {
        const descDisplay = mediaItem.querySelector('.description-display');
        const descEdit = mediaItem.querySelector('.description-edit');
        const saveBtn = mediaItem.querySelector('.save-description-btn');
        const cancelBtn = mediaItem.querySelector('.cancel-description-btn');
        
        descDisplay.style.display = 'block';
        descEdit.style.display = 'none';
        saveBtn.style.display = 'none';
        cancelBtn.style.display = 'none';
    }
    
    async saveTitle(mediaItem) {
        const mediaId = mediaItem.dataset.id;
        const titleEdit = mediaItem.querySelector('.title-edit');
        const newTitle = titleEdit.value.trim();
        
        if (!newTitle) {
            this.showMessage('Title cannot be empty', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/media/${mediaId}/update`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            });
            
            if (response.ok) {
                const titleDisplay = mediaItem.querySelector('.title-display');
                titleDisplay.textContent = newTitle;
                titleEdit.dataset.original = newTitle;
                
                this.cancelTitleEditing(mediaItem);
                this.showMessage('Title updated successfully', 'success');
            } else {
                const result = await response.json();
                throw new Error(result.message || 'Update failed');
            }
        } catch (error) {
            console.error('Update error:', error);
            this.showMessage('Failed to update title: ' + error.message, 'error');
            this.cancelTitleEditing(mediaItem);
        }
    }
    
    async saveDescription(mediaItem) {
        const mediaId = mediaItem.dataset.id;
        const descEdit = mediaItem.querySelector('.description-edit');
        const newDescription = descEdit.value.trim();
        
        try {
            const response = await fetch(`/api/media/${mediaId}/update`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ description: newDescription })
            });
            
            if (response.ok) {
                const descDisplay = mediaItem.querySelector('.description-display');
                descDisplay.textContent = newDescription || 'No description';
                
                this.cancelDescriptionEditing(mediaItem);
                this.showMessage('Description updated successfully', 'success');
            } else {
                const result = await response.json();
                throw new Error(result.message || 'Update failed');
            }
        } catch (error) {
            console.error('Update error:', error);
            this.showMessage('Failed to update description: ' + error.message, 'error');
            this.cancelDescriptionEditing(mediaItem);
        }
    }
    
    initLightbox() {
        if (!document.getElementById('lightbox')) {
            const lightboxHTML = `
                <div id="lightbox" class="lightbox" style="display: none; opacity: 0;">
                    <div class="lightbox-content">
                        <button class="lightbox-close">&times;</button>
                        <img src="" alt="" class="lightbox-image">
                        <div class="lightbox-caption"></div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', lightboxHTML);
            
            const lightbox = document.getElementById('lightbox');
            const closeBtn = lightbox.querySelector('.lightbox-close');
            
            closeBtn.addEventListener('click', () => this.closeLightbox());
            lightbox.addEventListener('click', (e) => {
                if (e.target === lightbox) this.closeLightbox();
            });
            
            document.addEventListener('keydown', (e) => {
                if (lightbox.style.display === 'flex' && e.key === 'Escape') {
                    this.closeLightbox();
                }
            });
        }
    }
    
    openLightbox(src, caption) {
        const lightbox = document.getElementById('lightbox');
        const lightboxImage = lightbox.querySelector('.lightbox-image');
        const lightboxCaption = lightbox.querySelector('.lightbox-caption');
        
        lightboxImage.src = src;
        lightboxImage.alt = caption;
        lightboxCaption.textContent = caption;
        
        lightbox.style.display = 'flex';
        setTimeout(() => {
            lightbox.style.opacity = '1';
        }, 10);
        
        document.body.style.overflow = 'hidden';
    }
    
    closeLightbox() {
        const lightbox = document.getElementById('lightbox');
        lightbox.style.opacity = '0';
        
        setTimeout(() => {
            lightbox.style.display = 'none';
            document.body.style.overflow = 'auto';
        }, 300);
    }
    
    showMessage(message, type) {
        const existingMsg = document.querySelector('.media-message');
        if (existingMsg) {
            existingMsg.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `media-message ${type}`;
        messageDiv.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            <span>${message}</span>
            <button class="close-message">&times;</button>
        `;
        
        const container = document.querySelector('.media-container') || document.querySelector('#mediaTab') || document.body;
        if (container) {
            container.prepend(messageDiv);
            
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.remove();
                }
            }, 5000);
            
            messageDiv.querySelector('.close-message').addEventListener('click', () => {
                messageDiv.remove();
            });
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mediaManager = new MediaManager();
});

// Add tab change listener - FIXED to prevent duplicate loads
document.addEventListener('tabChanged', (e) => {
    if (e.detail.tab === 'media' && window.mediaManager) {
        // Use debounced refresh instead of direct load
        window.mediaManager.debouncedGalleryRefresh();
    }
});