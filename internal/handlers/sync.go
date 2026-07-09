package handlers

import (
	"context"
	"crypto/md5"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"regexp"
	"time"

	"lexiqa-server/internal/models"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

var uuidRegex = regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)

// DeterministicUUID converts any string to a valid UUID v3 deterministically
func DeterministicUUID(input string) string {
	if input == "" {
		return "00000000-0000-0000-0000-000000000000"
	}
	if uuidRegex.MatchString(input) {
		return input
	}
	hasher := md5.New()
	hasher.Write([]byte(input))
	hash := hasher.Sum(nil)
	return fmt.Sprintf("%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
		hash[0], hash[1], hash[2], hash[3],
		hash[4], hash[5],
		hash[6]&0x0f|0x30,
		hash[7],
		hash[8]&0x3f|0x80,
		hash[9],
		hash[10], hash[11], hash[12], hash[13], hash[14], hash[15],
	)
}

// SyncHandler handles the client batch synchronization requests.
type SyncHandler struct {
	DB *pgxpool.Pool
}

// ServeHTTP implements the http.Handler interface
func (h *SyncHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req models.SyncBatchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body: "+err.Error(), http.StatusBadRequest)
		return
	}

	response := models.SyncBatchResponse{
		Results: make([]models.SyncResponseItem, 0, len(req.Batch)),
	}

	ctx := r.Context()

	for _, item := range req.Batch {
		err := h.processSyncItem(ctx, item)
		status := "synced"
		errStr := ""
		if err != nil {
			status = "error"
			errStr = err.Error()
			log.Printf("[SYNC] Error processing item %s of type %s: %v", item.ID, item.EntityType, err)
		}
		response.Results = append(response.Results, models.SyncResponseItem{
			OutboxID: item.ID,
			Status:   status,
			Error:    errStr,
		})
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(response)
}

func (h *SyncHandler) processSyncItem(ctx context.Context, item models.SyncOutboxItem) error {
	tx, err := h.DB.Begin(ctx)
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback(ctx)

	switch item.EntityType {
	case "courses":
		var course models.CourseModel
		if err := json.Unmarshal([]byte(item.Payload), &course); err != nil {
			return fmt.Errorf("failed to unmarshal course: %w", err)
		}
		courseID := DeterministicUUID(course.ID)
		teacherID := resolveUUIDPointer(course.TeacherID)

		if teacherID != nil {
			if err := ensureUserExists(ctx, tx, *teacherID, "teacher", "Docente Replicado"); err != nil {
				return err
			}
		}

		_, err = tx.Exec(ctx, `
			INSERT INTO courses (id, code, name, career, term, teacher_id)
			VALUES ($1, $2, $3, $4, $5, $6)
			ON CONFLICT (id) DO UPDATE SET
				code = EXCLUDED.code,
				name = EXCLUDED.name,
				career = EXCLUDED.career,
				term = EXCLUDED.term,
				teacher_id = EXCLUDED.teacher_id;
		`, courseID, course.Code, course.Name, course.Career, course.Term, teacherID)
		if err != nil {
			return fmt.Errorf("failed to upsert course: %w", err)
		}

	case "class_sessions":
		var sess models.ClassSessionModel
		if err := json.Unmarshal([]byte(item.Payload), &sess); err != nil {
			return fmt.Errorf("failed to unmarshal session: %w", err)
		}

		sessionID := DeterministicUUID(sess.ID)
		courseID := resolveUUIDPointer(sess.CourseID)
		teacherID := resolveUUIDPointer(sess.TeacherID)
		studentID := resolveUUIDPointer(sess.StudentID)

		// Ensure FKs
		if courseID != nil {
			if err := ensureCourseExists(ctx, tx, *courseID, sess.CourseName); err != nil {
				return err
			}
		}
		if teacherID != nil {
			if err := ensureUserExists(ctx, tx, *teacherID, "teacher", "Docente Replicado"); err != nil {
				return err
			}
		}
		if studentID != nil {
			if err := ensureUserExists(ctx, tx, *studentID, "student", "Estudiante Replicado"); err != nil {
				return err
			}
		} else {
			// Fallback/Default student to satisfy Postgres constraint if needed
			defaultStudentID := DeterministicUUID("default_student_m1")
			if err := ensureUserExists(ctx, tx, defaultStudentID, "student", "Estudiante por Defecto"); err != nil {
				return err
			}
			studentID = &defaultStudentID
		}

		startedAt := time.UnixMilli(sess.StartedAt)
		var endedAt *time.Time
		if sess.EndedAt != nil {
			t := time.UnixMilli(*sess.EndedAt)
			endedAt = &t
		}

		_, err = tx.Exec(ctx, `
			INSERT INTO class_sessions (id, local_id, course_id, teacher_id, student_id, captor_device_id, session_title, status, started_at, ended_at, duration_sec, sync_status, version)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'synced', $12)
			ON CONFLICT (id) DO UPDATE SET
				status = EXCLUDED.status,
				ended_at = EXCLUDED.ended_at,
				duration_sec = EXCLUDED.duration_sec,
				session_title = EXCLUDED.session_title,
				sync_status = 'synced',
				synced_at = now(),
				version = EXCLUDED.version;
		`, sessionID, sessionID, courseID, teacherID, studentID, resolveUUIDPointer(sess.CaptorDeviceID), sess.SessionTitle, sess.Status, startedAt, endedAt, sess.DurationSec, sess.Version)
		if err != nil {
			return fmt.Errorf("failed to upsert session: %w", err)
		}

	case "transcript_segments":
		var seg models.TranscriptSegmentModel
		if err := json.Unmarshal([]byte(item.Payload), &seg); err != nil {
			return fmt.Errorf("failed to unmarshal segment: %w", err)
		}

		segmentID := DeterministicUUID(seg.ID)
		sessionID := DeterministicUUID(seg.SessionID)

		if err := ensureSessionExists(ctx, tx, sessionID); err != nil {
			return err
		}

		createdAt := time.UnixMilli(seg.CreatedAt)

		_, err = tx.Exec(ctx, `
			INSERT INTO transcript_segments (id, local_id, session_id, sequence, raw_text, text, status, offset_ms, created_at, sync_status, version)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'synced', $10)
			ON CONFLICT (id) DO UPDATE SET
				text = EXCLUDED.text,
				raw_text = EXCLUDED.raw_text,
				status = EXCLUDED.status,
				sync_status = 'synced',
				version = EXCLUDED.version;
		`, segmentID, segmentID, sessionID, seg.Sequence, seg.RawText, seg.Text, seg.Status, seg.OffsetMs, createdAt, seg.Version)
		if err != nil {
			return fmt.Errorf("failed to upsert segment: %w", err)
		}

	case "formula_blocks":
		var fb models.FormulaBlockModel
		if err := json.Unmarshal([]byte(item.Payload), &fb); err != nil {
			return fmt.Errorf("failed to unmarshal formula: %w", err)
		}

		formulaID := DeterministicUUID(fb.ID)
		sessionID := DeterministicUUID(fb.SessionID)
		segmentID := resolveUUIDPointer(fb.SegmentID)

		if err := ensureSessionExists(ctx, tx, sessionID); err != nil {
			return err
		}
		if segmentID != nil {
			if err := ensureSegmentExists(ctx, tx, *segmentID, sessionID); err != nil {
				return err
			}
		}

		_, err = tx.Exec(ctx, `
			INSERT INTO formula_blocks (id, session_id, segment_id, latex, offset_ms, sync_status)
			VALUES ($1, $2, $3, $4, $5, 'synced')
			ON CONFLICT (id) DO UPDATE SET
				latex = EXCLUDED.latex,
				sync_status = 'synced';
		`, formulaID, sessionID, segmentID, fb.Latex, fb.OffsetMs)
		if err != nil {
			return fmt.Errorf("failed to upsert formula: %w", err)
		}

	case "notes":
		var note models.NoteModel
		if err := json.Unmarshal([]byte(item.Payload), &note); err != nil {
			return fmt.Errorf("failed to unmarshal note: %w", err)
		}

		noteID := DeterministicUUID(note.ID)
		sessionID := DeterministicUUID(note.SessionID)
		segmentID := resolveUUIDPointer(note.SegmentID)
		userID := DeterministicUUID(note.UserID)

		if err := ensureSessionExists(ctx, tx, sessionID); err != nil {
			return err
		}
		if segmentID != nil {
			if err := ensureSegmentExists(ctx, tx, *segmentID, sessionID); err != nil {
				return err
			}
		}
		if err := ensureUserExists(ctx, tx, userID, "student", "Estudiante Nota"); err != nil {
			return err
		}

		createdAt := time.UnixMilli(note.CreatedAt)

		_, err = tx.Exec(ctx, `
			INSERT INTO notes (id, session_id, segment_id, user_id, content, offset_ms, created_at, sync_status)
			VALUES ($1, $2, $3, $4, $5, $6, $7, 'synced')
			ON CONFLICT (id) DO UPDATE SET
				content = EXCLUDED.content,
				sync_status = 'synced';
		`, noteID, sessionID, segmentID, userID, note.Content, note.OffsetMs, createdAt)
		if err != nil {
			return fmt.Errorf("failed to upsert note: %w", err)
		}

	case "bookmarks":
		var bm models.BookmarkModel
		if err := json.Unmarshal([]byte(item.Payload), &bm); err != nil {
			return fmt.Errorf("failed to unmarshal bookmark: %w", err)
		}

		bookmarkID := DeterministicUUID(bm.ID)
		sessionID := DeterministicUUID(bm.SessionID)

		if err := ensureSessionExists(ctx, tx, sessionID); err != nil {
			return err
		}

		_, err = tx.Exec(ctx, `
			INSERT INTO bookmarks (id, session_id, offset_ms, label, sync_status)
			VALUES ($1, $2, $3, $4, 'synced')
			ON CONFLICT (id) DO UPDATE SET
				label = EXCLUDED.label,
				sync_status = 'synced';
		`, bookmarkID, sessionID, bm.OffsetMs, bm.Label)
		if err != nil {
			return fmt.Errorf("failed to upsert bookmark: %w", err)
		}

	default:
		return fmt.Errorf("unsupported entity type: %s", item.EntityType)
	}

	return tx.Commit(ctx)
}

// Helper methods to ensure constraints are satisfied

func resolveUUIDPointer(input *string) *string {
	if input == nil || *input == "" {
		return nil
	}
	val := DeterministicUUID(*input)
	return &val
}

func ensureUserExists(ctx context.Context, tx pgx.Tx, userID string, role string, name string) error {
	var exists bool
	err := tx.QueryRow(ctx, "SELECT EXISTS(SELECT 1 FROM users WHERE id = $1)", userID).Scan(&exists)
	if err != nil {
		return err
	}
	if !exists {
		_, err = tx.Exec(ctx, `
			INSERT INTO users (id, email, role, display_name)
			VALUES ($1, $2, $3, $4)
			ON CONFLICT (id) DO NOTHING;
		`, userID, fmt.Sprintf("%s_%s@lexiqa.edu", role, userID[:8]), role, name)
		if err != nil {
			return fmt.Errorf("failed to auto-create user %s: %w", userID, err)
		}
	}
	return nil
}

func ensureCourseExists(ctx context.Context, tx pgx.Tx, courseID string, courseName string) error {
	var exists bool
	err := tx.QueryRow(ctx, "SELECT EXISTS(SELECT 1 FROM courses WHERE id = $1)", courseID).Scan(&exists)
	if err != nil {
		return err
	}
	if !exists {
		if courseName == "" {
			courseName = "Materia Replicada " + courseID[:4]
		}
		_, err = tx.Exec(ctx, `
			INSERT INTO courses (id, name, created_at)
			VALUES ($1, $2, now())
			ON CONFLICT (id) DO NOTHING;
		`, courseID, courseName)
		if err != nil {
			return fmt.Errorf("failed to auto-create course %s: %w", courseID, err)
		}
	}
	return nil
}

func ensureSessionExists(ctx context.Context, tx pgx.Tx, sessionID string) error {
	var exists bool
	err := tx.QueryRow(ctx, "SELECT EXISTS(SELECT 1 FROM class_sessions WHERE id = $1)", sessionID).Scan(&exists)
	if err != nil {
		return err
	}
	if !exists {
		defaultStudentID := DeterministicUUID("default_student_m1")
		if err := ensureUserExists(ctx, tx, defaultStudentID, "student", "Estudiante por Defecto"); err != nil {
			return err
		}

		_, err = tx.Exec(ctx, `
			INSERT INTO class_sessions (id, student_id, session_title, status, started_at, sync_status)
			VALUES ($1, $2, 'Sesión Replicada', 'completed', now(), 'synced')
			ON CONFLICT (id) DO NOTHING;
		`, sessionID, defaultStudentID)
		if err != nil {
			return fmt.Errorf("failed to auto-create session %s: %w", sessionID, err)
		}
	}
	return nil
}

func ensureSegmentExists(ctx context.Context, tx pgx.Tx, segmentID string, sessionID string) error {
	var exists bool
	err := tx.QueryRow(ctx, "SELECT EXISTS(SELECT 1 FROM transcript_segments WHERE id = $1)", segmentID).Scan(&exists)
	if err != nil {
		return err
	}
	if !exists {
		_, err = tx.Exec(ctx, `
			INSERT INTO transcript_segments (id, session_id, sequence, raw_text, text, status, offset_ms, created_at, sync_status)
			VALUES ($1, $2, 0, '', '', 'final', 0, now(), 'synced')
			ON CONFLICT (id) DO NOTHING;
		`, segmentID, sessionID)
		if err != nil {
			return fmt.Errorf("failed to auto-create segment %s: %w", segmentID, err)
		}
	}
	return nil
}
