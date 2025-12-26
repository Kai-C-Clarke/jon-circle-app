-- Migration: Add memory_media linking table
-- Run this against your database to enable manual photo-to-memory linking

-- Create the linking table
CREATE TABLE IF NOT EXISTS memory_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER NOT NULL,
    media_id INTEGER NOT NULL,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE,
    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE,
    UNIQUE(memory_id, media_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_memory_media_memory_id ON memory_media(memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_media_media_id ON memory_media(media_id);

-- Verify the structure
SELECT 'Migration complete. memory_media table created.' AS status;
