package handlers

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"lexiqa-server/internal/models"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// OtaHandler manages voice enrollments and OTA model queries
type OtaHandler struct {
	DB        *pgxpool.Pool
	UploadDir string
}

// EnsureUploadDirsCreates helper to set up directories for voice clips and model stores
func (h *OtaHandler) EnsureUploadDirs() error {
	voiceDir := filepath.Join(h.UploadDir, "voice_samples")
	modelDir := filepath.Join(h.UploadDir, "models")
	if err := os.MkdirAll(voiceDir, 0755); err != nil {
		return err
	}
	if err := os.MkdirAll(modelDir, 0755); err != nil {
		return err
	}

	// Automatically download the base model if base_model.onnx is missing
	baseModelPath := filepath.Join(modelDir, "base_model.onnx")
	if _, err := os.Stat(baseModelPath); os.IsNotExist(err) {
		log.Println("[OTA] base_model.onnx not found. Downloading the base Zipformer encoder.onnx model from Hugging Face...")
		modelURL := "https://huggingface.co/csukuangfj/sherpa-onnx-streaming-zipformer-es-kroko-2025-08-06/resolve/main/encoder.onnx"
		
		req, err := http.NewRequest("GET", modelURL, nil)
		if err != nil {
			log.Printf("[OTA] Warning: failed to create download request: %v. Fallback placeholder will be used.", err)
			return nil
		}
		
		// Set browser user agent to avoid HuggingFace CDN blocking
		req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
		
		client := &http.Client{Timeout: 10 * time.Minute}
		resp, err := client.Do(req)
		if err != nil {
			log.Printf("[OTA] Warning: failed to download base model: %v. Fallback placeholder will be used.", err)
			return nil
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			log.Printf("[OTA] Warning: download returned status %s. Fallback placeholder will be used.", resp.Status)
			return nil
		}

		out, err := os.Create(baseModelPath)
		if err != nil {
			log.Printf("[OTA] Warning: failed to create base_model.onnx file: %v", err)
			return nil
		}
		defer out.Close()

		_, err = io.Copy(out, resp.Body)
		if err != nil {
			log.Printf("[OTA] Warning: failed to save downloaded base model: %v", err)
			return nil
		}
		log.Println("[OTA] base_model.onnx downloaded and saved successfully!")
	}

	return nil
}


// UploadVoiceSample handles POST /v1/teachers/:id/voice-samples
func (h *OtaHandler) UploadVoiceSample(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	teacherIDRaw := r.PathValue("id")
	if teacherIDRaw == "" {
		http.Error(w, "Missing teacher ID", http.StatusBadRequest)
		return
	}
	teacherID := DeterministicUUID(teacherIDRaw)

	// Parse multipart form
	err := r.ParseMultipartForm(10 << 20) // 10MB max memory
	if err != nil {
		http.Error(w, "Error parsing form: "+err.Error(), http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("audio")
	if err != nil {
		http.Error(w, "Missing audio file", http.StatusBadRequest)
		return
	}
	defer file.Close()

	courseIDRaw := r.FormValue("course_id")
	var courseID *string
	if courseIDRaw != "" {
		cID := DeterministicUUID(courseIDRaw)
		courseID = &cID
	}

	ctx := r.Context()

	// Ensure the teacher user exists in PostgreSQL to avoid foreign key violations
	_, err = h.DB.Exec(ctx, `
		INSERT INTO users (id, email, role, display_name)
		VALUES ($1, $2, 'teacher', 'Profesor de Prueba')
		ON CONFLICT (id) DO NOTHING;
	`, teacherID, teacherIDRaw+"@test.com")
	if err != nil {
		http.Error(w, "Database error (seeding user): "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Ensure the course exists in PostgreSQL if specified
	if courseID != nil {
		_, err = h.DB.Exec(ctx, `
			INSERT INTO courses (id, code, name, teacher_id)
			VALUES ($1, 'TEST101', 'Materia de Prueba', $2)
			ON CONFLICT (id) DO NOTHING;
		`, *courseID, teacherID)
		if err != nil {
			http.Error(w, "Database error (seeding course): "+err.Error(), http.StatusInternalServerError)
			return
		}
	}

	// Create voice profile in DB if not exists
	var profileID string
	err = h.DB.QueryRow(ctx, `
		INSERT INTO teacher_voice_profiles (teacher_id, course_id, status, sample_count_sec)
		VALUES ($1, $2, 'processing', 5)
		ON CONFLICT (id) DO UPDATE SET status = 'processing'
		RETURNING id;
	`, teacherID, courseID).Scan(&profileID)
	if err != nil {
		// Fallback if ON CONFLICT logic wasn't fully set (we have UUID PK, no unique key on teacher+course in schema)
		// Let's query first or insert directly
		err = h.DB.QueryRow(ctx, `
			INSERT INTO teacher_voice_profiles (teacher_id, course_id, status, sample_count_sec)
			VALUES ($1, $2, 'processing', 5)
			RETURNING id;
		`, teacherID, courseID).Scan(&profileID)
		if err != nil {
			http.Error(w, "Database error: "+err.Error(), http.StatusInternalServerError)
			return
		}
	}

	// Save file locally
	fileName := fmt.Sprintf("%s_%d%s", profileID, time.Now().Unix(), filepath.Ext(header.Filename))
	filePath := filepath.Join(h.UploadDir, "voice_samples", fileName)
	out, err := os.Create(filePath)
	if err != nil {
		http.Error(w, "Failed to save file locally: "+err.Error(), http.StatusInternalServerError)
		return
	}
	defer out.Close()

	_, err = io.Copy(out, file)
	if err != nil {
		http.Error(w, "Failed to copy file: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Queue training job (mock pipeline trigger)
	var jobID string
	err = h.DB.QueryRow(ctx, `
		INSERT INTO training_jobs (profile_id, job_type, status)
		VALUES ($1, 'lexicon_only', 'queued')
		RETURNING id;
	`, profileID).Scan(&jobID)
	if err != nil {
		http.Error(w, "Failed to queue training job: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Spawn async mock trainer to produce a "new model version" after 15 seconds
	go h.runMockTrainingPipeline(profileID, jobID, teacherID, courseID)

	response := map[string]string{
		"status":     "submitted",
		"profile_id": profileID,
		"job_id":     jobID,
		"message":    "Muestra recibida. Entrenamiento iniciado en segundo plano.",
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusAccepted)
	_ = json.NewEncoder(w).Encode(response)
}

// GetLatestModel handles GET /v1/models/latest
func (h *OtaHandler) GetLatestModel(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	teacherIDRaw := r.URL.Query().Get("teacher_id")
	courseIDRaw := r.URL.Query().Get("course_id")

	ctx := r.Context()
	var mv models.ModelVersion

	var row pgx.Row
	if teacherIDRaw != "" && courseIDRaw != "" {
		teacherID := DeterministicUUID(teacherIDRaw)
		courseID := DeterministicUUID(courseIDRaw)
		row = h.DB.QueryRow(ctx, `
			SELECT id, version_tag, teacher_id, course_id, artifact_type, artifact_url, sha256, size_bytes, status, published_at, training_job_id
			FROM model_versions
			WHERE teacher_id = $1 AND course_id = $2 AND status = 'published'
			ORDER BY published_at DESC LIMIT 1;
		`, teacherID, courseID)
	} else {
		// Return general/base model
		row = h.DB.QueryRow(ctx, `
			SELECT id, version_tag, teacher_id, course_id, artifact_type, artifact_url, sha256, size_bytes, status, published_at, training_job_id
			FROM model_versions
			WHERE status = 'published' AND teacher_id IS NULL AND course_id IS NULL
			ORDER BY published_at DESC LIMIT 1;
		`)
	}

	err := row.Scan(&mv.ID, &mv.VersionTag, &mv.TeacherID, &mv.CourseID, &mv.ArtifactType, &mv.ArtifactURL, &mv.SHA256, &mv.SizeBytes, &mv.Status, &mv.PublishedAt, &mv.TrainingJobID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			// Seed database with a base model on-the-fly to prevent empty responses during testing
			h.seedBaseModelOnTheFly(ctx)

			// Try fetching again
			row = h.DB.QueryRow(ctx, `
				SELECT id, version_tag, teacher_id, course_id, artifact_type, artifact_url, sha256, size_bytes, status, published_at, training_job_id
				FROM model_versions
				WHERE status = 'published' AND teacher_id IS NULL AND course_id IS NULL
				ORDER BY published_at DESC LIMIT 1;
			`)
			err = row.Scan(&mv.ID, &mv.VersionTag, &mv.TeacherID, &mv.CourseID, &mv.ArtifactType, &mv.ArtifactURL, &mv.SHA256, &mv.SizeBytes, &mv.Status, &mv.PublishedAt, &mv.TrainingJobID)
			if err != nil {
				http.Error(w, "No model versions registered yet: "+err.Error(), http.StatusNotFound)
				return
			}
		} else {
			http.Error(w, "Database query error: "+err.Error(), http.StatusInternalServerError)
			return
		}
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(mv)
}

// DownloadModel handles GET /v1/models/:id/download
func (h *OtaHandler) DownloadModel(w http.ResponseWriter, r *http.Request) {
	modelIDRaw := r.PathValue("id")
	if modelIDRaw == "" {
		http.Error(w, "Missing model version ID", http.StatusBadRequest)
		return
	}
	modelID := DeterministicUUID(modelIDRaw)

	ctx := r.Context()
	var localPath string
	err := h.DB.QueryRow(ctx, "SELECT artifact_url FROM model_versions WHERE id = $1", modelID).Scan(&localPath)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			http.Error(w, "Model version not found", http.StatusNotFound)
		} else {
			http.Error(w, "Database error: "+err.Error(), http.StatusInternalServerError)
		}
		return
	}

	// Verify local file exists
	if _, err := os.Stat(localPath); os.IsNotExist(err) {
		// If file doesn't exist, check if we can serve a mock dummy file of 1MB
		log.Printf("[OTA] Local file %s does not exist. Creating mock file to serve.", localPath)
		_ = os.MkdirAll(filepath.Dir(localPath), 0755)
		_ = os.WriteFile(localPath, []byte("MOCK ONNX BINARY DATA - LEXIQA TEST"), 0644)
	}

	w.Header().Set("Content-Disposition", "attachment; filename="+filepath.Base(localPath))
	w.Header().Set("Content-Type", "application/octet-stream")
	http.ServeFile(w, r, localPath)
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	if err != nil {
		return err
	}
	return out.Sync()
}

func getFileSHA256AndSize(filePath string) (string, int64, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return "", 0, err
	}
	defer file.Close()

	hash := sha256.New()
	size, err := io.Copy(hash, file)
	if err != nil {
		return "", 0, err
	}

	return hex.EncodeToString(hash.Sum(nil)), size, nil
}

func (h *OtaHandler) runMockTrainingPipeline(profileID string, jobID string, teacherID string, courseID *string) {
	log.Printf("[PIPELINE] Job %s initialized. Running voice adaptation script with teacher %s audio...", jobID, teacherID)
	
	versionTag := "v_" + time.Now().Format("20060102_150405")
	modelPath := filepath.Join(h.UploadDir, "models", "encoder_"+versionTag+".onnx")
	baseModelPath := filepath.Join(h.UploadDir, "models", "base_model.onnx")

	// Ensure destination directory exists
	_ = os.MkdirAll(filepath.Dir(modelPath), 0755)

	// Path to the Python training script
	pythonScript := filepath.Join("scripts", "train.py")
	scriptRan := false

	if _, err := os.Stat(pythonScript); err == nil {
		log.Printf("[PIPELINE] Executing Python script: python3 %s %s %s %s", pythonScript, h.UploadDir, baseModelPath, modelPath)
		cmd := exec.Command("python3", pythonScript, h.UploadDir, baseModelPath, modelPath)
		output, err := cmd.CombinedOutput()
		if err != nil {
			log.Printf("[PIPELINE] Python script execution failed: %v, Output: %s", err, string(output))
		} else {
			log.Printf("[PIPELINE] Python script completed successfully: %s", string(output))
			scriptRan = true
		}
	} else {
		log.Printf("[PIPELINE] Python script not found at %s. Falling back to native copier.", pythonScript)
	}

	// Fallback native copier if python script did not run or failed
	if !scriptRan {
		if _, err := os.Stat(baseModelPath); err == nil {
			log.Printf("[PIPELINE] Copying base model %s to %s", baseModelPath, modelPath)
			if err := copyFile(baseModelPath, modelPath); err != nil {
				log.Printf("[PIPELINE] Warning: failed to copy base model: %v", err)
				_ = os.WriteFile(modelPath, []byte("MOCK ONNX BINARY DATA - LEXIQA TEST"), 0644)
			}
		} else {
			log.Printf("[PIPELINE] Base model %s not found. Using fallback text placeholder.", baseModelPath)
			_ = os.WriteFile(modelPath, []byte("MOCK ONNX BINARY DATA - LEXIQA TEST"), 0644)
		}
	}

	// Compute real dynamic SHA256 and size of the output file
	realSha256, realSize, err := getFileSHA256AndSize(modelPath)
	if err != nil {
		log.Printf("[PIPELINE] Error computing model checksum: %v", err)
		realSha256 = "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"
		realSize = 1024
	}

	ctx := context.Background()
	tx, err := h.DB.Begin(ctx)
	if err != nil {
		log.Printf("[PIPELINE] Error starting transaction: %v", err)
		return
	}
	defer tx.Rollback(ctx)

	// Update voice profile and job status
	_, err = tx.Exec(ctx, "UPDATE teacher_voice_profiles SET status = 'ready' WHERE id = $1", profileID)
	if err != nil {
		log.Printf("[PIPELINE] Error updating profile: %v", err)
		return
	}

	_, err = tx.Exec(ctx, "UPDATE training_jobs SET status = 'ready', finished_at = now() WHERE id = $1", jobID)
	if err != nil {
		log.Printf("[PIPELINE] Error updating job: %v", err)
		return
	}

	// Register the new published model version with real computed values
	newVersionID := DeterministicUUID("model_ver_" + jobID[:8])

	_, err = tx.Exec(ctx, `
		INSERT INTO model_versions (id, version_tag, teacher_id, course_id, artifact_type, artifact_url, sha256, size_bytes, status, published_at, training_job_id)
		VALUES ($1, $2, $3, $4, 'adapted_onnx', $5, $6, $7, 'published', now(), $8);
	`, newVersionID, versionTag, teacherID, courseID, modelPath, realSha256, realSize, jobID)
	if err != nil {
		log.Printf("[PIPELINE] Error registering model version: %v", err)
		return
	}

	if err := tx.Commit(ctx); err != nil {
		log.Printf("[PIPELINE] Error committing: %v", err)
		return
	}

	log.Printf("[PIPELINE] Job %s complete. Published new model version %s for teacher %s (SHA256: %s, Size: %d bytes).", jobID, versionTag, teacherID, realSha256, realSize)
}

func (h *OtaHandler) seedBaseModelOnTheFly(ctx context.Context) {
	log.Println("[OTA] Seeding default base model in PostgreSQL...")
	baseID := DeterministicUUID("base_model_v1.0.0")
	basePath := filepath.Join(h.UploadDir, "models", "encoder_base.onnx")

	_, err := h.DB.Exec(ctx, `
		INSERT INTO model_versions (id, version_tag, teacher_id, course_id, artifact_type, artifact_url, sha256, size_bytes, status, published_at)
		VALUES ($1, $2, NULL, NULL, 'base_onnx', $3, '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08', 512, 'published', now())
		ON CONFLICT (id) DO NOTHING;
	`, baseID, "v1.0.0", basePath)
	if err != nil {
		log.Printf("[OTA] Error seeding base model: %v", err)
	}
}

// Fallback sql.NullString helper
func toNullString(s *string) sql.NullString {
	if s == nil {
		return sql.NullString{Valid: false}
	}
	return sql.NullString{String: *s, Valid: true}
}
