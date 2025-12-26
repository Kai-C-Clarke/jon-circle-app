import React, { useState, useEffect } from 'react';
import { Camera, X, Plus } from 'lucide-react';

/**
 * MediaLinker Component
 * Allows users to select and link media items to a memory
 * 
 * Props:
 *   memoryId: ID of the memory to link media to
 *   onUpdate: Callback when media links are updated
 */
const MediaLinker = ({ memoryId, onUpdate }) => {
  const [availableMedia, setAvailableMedia] = useState([]);
  const [linkedMedia, setLinkedMedia] = useState([]);
  const [isSelecting, setIsSelecting] = useState(false);
  const [loading, setLoading] = useState(true);

  // Load available media and currently linked media
  useEffect(() => {
    if (memoryId) {
      loadMediaData();
    }
  }, [memoryId]);

  const loadMediaData = async () => {
    setLoading(true);
    try {
      // Load all available media
      const availableRes = await fetch('/api/media/available');
      const availableData = await availableRes.json();
      
      // Load currently linked media
      const linkedRes = await fetch(`/api/memories/${memoryId}/media`);
      const linkedData = await linkedRes.json();
      
      if (availableData.success) {
        setAvailableMedia(availableData.media);
      }
      
      if (linkedData.success) {
        setLinkedMedia(linkedData.media);
      }
    } catch (error) {
      console.error('Error loading media:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddMedia = async (mediaId) => {
    try {
      const response = await fetch(`/api/memories/${memoryId}/media/${mediaId}`, {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (data.success) {
        await loadMediaData();
        if (onUpdate) onUpdate();
      }
    } catch (error) {
      console.error('Error adding media:', error);
    }
  };

  const handleRemoveMedia = async (mediaId) => {
    try {
      const response = await fetch(`/api/memories/${memoryId}/media/${mediaId}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      
      if (data.success) {
        await loadMediaData();
        if (onUpdate) onUpdate();
      }
    } catch (error) {
      console.error('Error removing media:', error);
    }
  };

  const handleReorder = async (newOrder) => {
    try {
      const mediaIds = newOrder.map(m => m.id);
      
      const response = await fetch(`/api/memories/${memoryId}/media`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ media_ids: mediaIds })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setLinkedMedia(newOrder);
        if (onUpdate) onUpdate();
      }
    } catch (error) {
      console.error('Error reordering media:', error);
    }
  };

  const moveUp = (index) => {
    if (index === 0) return;
    const newOrder = [...linkedMedia];
    [newOrder[index - 1], newOrder[index]] = [newOrder[index], newOrder[index - 1]];
    handleReorder(newOrder);
  };

  const moveDown = (index) => {
    if (index === linkedMedia.length - 1) return;
    const newOrder = [...linkedMedia];
    [newOrder[index], newOrder[index + 1]] = [newOrder[index + 1], newOrder[index]];
    handleReorder(newOrder);
  };

  if (loading) {
    return <div className="text-gray-500">Loading media...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Linked Media Display */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-gray-700">Linked Photos</h3>
          <button
            onClick={() => setIsSelecting(!isSelecting)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus size={16} />
            Add Photos
          </button>
        </div>

        {linkedMedia.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
            <Camera size={40} className="mx-auto text-gray-400 mb-2" />
            <p className="text-gray-500">No photos linked to this memory</p>
            <p className="text-sm text-gray-400 mt-1">Click "Add Photos" to select images</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {linkedMedia.map((media, index) => (
              <div key={media.id} className="relative group">
                <img
                  src={`/uploads/${media.filename}`}
                  alt={media.title || media.original_filename}
                  className="w-full h-40 object-cover rounded-lg"
                />
                
                {/* Overlay controls */}
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-all rounded-lg flex items-center justify-center gap-2">
                  <button
                    onClick={() => moveUp(index)}
                    disabled={index === 0}
                    className="opacity-0 group-hover:opacity-100 px-2 py-1 bg-white text-gray-700 rounded text-sm disabled:opacity-50"
                  >
                    ↑
                  </button>
                  <button
                    onClick={() => moveDown(index)}
                    disabled={index === linkedMedia.length - 1}
                    className="opacity-0 group-hover:opacity-100 px-2 py-1 bg-white text-gray-700 rounded text-sm disabled:opacity-50"
                  >
                    ↓
                  </button>
                  <button
                    onClick={() => handleRemoveMedia(media.id)}
                    className="opacity-0 group-hover:opacity-100 p-2 bg-red-600 text-white rounded-full hover:bg-red-700"
                  >
                    <X size={16} />
                  </button>
                </div>
                
                {/* Caption */}
                <div className="mt-1 text-xs text-gray-600 truncate">
                  {media.title || media.original_filename}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Media Selection Modal */}
      {isSelecting && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="font-semibold text-lg">Select Photos to Link</h3>
              <button
                onClick={() => setIsSelecting(false)}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <X size={20} />
              </button>
            </div>

            {/* Media Grid */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="grid grid-cols-3 gap-3">
                {availableMedia.map((media) => {
                  const isLinked = linkedMedia.some(m => m.id === media.id);
                  
                  return (
                    <div
                      key={media.id}
                      onClick={() => !isLinked && handleAddMedia(media.id)}
                      className={`relative cursor-pointer rounded-lg overflow-hidden ${
                        isLinked ? 'opacity-50 cursor-not-allowed' : 'hover:ring-2 hover:ring-blue-500'
                      }`}
                    >
                      <img
                        src={`/uploads/${media.filename}`}
                        alt={media.title || media.original_filename}
                        className="w-full h-32 object-cover"
                      />
                      
                      {isLinked && (
                        <div className="absolute inset-0 bg-blue-600 bg-opacity-30 flex items-center justify-center">
                          <span className="bg-white px-2 py-1 rounded text-xs font-medium">
                            Already Linked
                          </span>
                        </div>
                      )}
                      
                      <div className="p-2 bg-white">
                        <div className="text-xs font-medium truncate">
                          {media.title || media.original_filename}
                        </div>
                        {media.year && (
                          <div className="text-xs text-gray-500">{media.year}</div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t bg-gray-50">
              <button
                onClick={() => setIsSelecting(false)}
                className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MediaLinker;
