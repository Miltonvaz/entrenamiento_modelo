package models

import "time"

// SyncOutboxItem represents an item in the client's sync queue
type SyncOutboxItem struct {
	ID            string `json:"id"`
	EntityType    string `json:"entity_type"`
	EntityLocalID string `json:"entity_local_id"`
	Operation     string `json:"operation"`
	Payload       string `json:"payload"` // JSON string of the entity
	RetryCount    int    `json:"retry_count"`
	CreatedAt     int64  `json:"created_at"`
}

// SyncBatchRequest represents the batch payload sent from Flutter
type SyncBatchRequest struct {
	DeviceID string           `json:"device_id"`
	Batch    []SyncOutboxItem `json:"batch"`
}

// SyncResponseItem represents the sync status of a single outbox item
type SyncResponseItem struct {
	OutboxID string `json:"outbox_id"`
	Status   string `json:"status"` // "synced" or "error"
	Error    string `json:"error,omitempty"`
}

// SyncBatchResponse is returned to the client
type SyncBatchResponse struct {
	Results []SyncResponseItem `json:"results"`
}

// CourseModel matches the local and remote course entity
type CourseModel struct {
	ID         string    `json:"id"`
	Code       string    `json:"code"`
	Name       string    `json:"name"`
	Career     string    `json:"career"`
	Term       string    `json:"term"`
	TeacherID  *string   `json:"teacher_id"`
	CreatedAt  time.Time `json:"created_at"`
}

// ClassSessionModel matches the local class session row
type ClassSessionModel struct {
	ID             string  `json:"id"`
	CourseID       *string `json:"course_id"`
	CourseName     string  `json:"course_name"`
	SessionTitle   string  `json:"session_title"`
	TeacherID      *string `json:"teacher_id"`
	StudentID      *string `json:"student_id"`
	CaptorDeviceID *string `json:"captor_device_id"`
	Status         string  `json:"status"`
	StartedAt      int64   `json:"started_at"` // milliseconds epoch
	EndedAt        *int64  `json:"ended_at"`   // milliseconds epoch
	DurationSec    *int    `json:"duration_sec"`
	Version        int     `json:"version"`
}

// TranscriptSegmentModel matches the transcript segment row
type TranscriptSegmentModel struct {
	ID        string `json:"id"`
	SessionID string `json:"session_id"`
	Sequence  int    `json:"sequence"`
	RawText   string `json:"raw_text"`
	Text      string `json:"text"`
	Status    string `json:"status"`
	OffsetMs  int    `json:"offset_ms"`
	CreatedAt int64  `json:"created_at"` // milliseconds epoch
	Version   int    `json:"version"`
}

// FormulaBlockModel matches formula_blocks row
type FormulaBlockModel struct {
	ID        string  `json:"id"`
	SessionID string  `json:"session_id"`
	SegmentID *string `json:"segment_id"`
	Latex     string  `json:"latex"`
	OffsetMs  int     `json:"offset_ms"`
}

// NoteModel matches notes row
type NoteModel struct {
	ID        string  `json:"id"`
	SessionID string  `json:"session_id"`
	SegmentID *string `json:"segment_id"`
	UserID    string  `json:"user_id"`
	Content   string  `json:"content"`
	OffsetMs  *int    `json:"offset_ms"`
	CreatedAt int64   `json:"created_at"` // milliseconds epoch
}

// BookmarkModel matches bookmarks row
type BookmarkModel struct {
	ID        string `json:"id"`
	SessionID string `json:"session_id"`
	OffsetMs  int    `json:"offset_ms"`
	Label     string `json:"label"`
	CreatedAt int64  `json:"created_at"` // milliseconds epoch
}

// TeacherVoiceProfile represents teacher voice enrollment metadata
type TeacherVoiceProfile struct {
	ID             string    `json:"id"`
	TeacherID      string    `json:"teacher_id"`
	CourseID       *string   `json:"course_id"`
	Status         string    `json:"status"`
	SampleCountSec int       `json:"sample_count_sec"`
	EnrolledAt     time.Time `json:"enrolled_at"`
	CreatedAt      time.Time `json:"created_at"`
}

// ModelVersion represents a compiled ONNX model
type ModelVersion struct {
	ID            string     `json:"id"`
	VersionTag    string     `json:"version_tag"`
	TeacherID     *string    `json:"teacher_id"`
	CourseID      *string    `json:"course_id"`
	ArtifactType  string     `json:"artifact_type"`
	ArtifactURL   string     `json:"artifact_url"`
	SHA256        string     `json:"sha256"`
	SizeBytes     int64      `json:"size_bytes"`
	Status        string     `json:"status"`
	PublishedAt   *time.Time `json:"published_at"`
	TrainingJobID *string    `json:"training_job_id"`
}
