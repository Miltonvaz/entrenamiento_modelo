package main

import (
	"log"
	"net/http"
	"os"

	"lexiqa-server/internal/db"
	"lexiqa-server/internal/handlers"
)

func main() {
	// 1. Load Configurations from environment variables
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		// Fallback database configuration using milton123 credentials
		databaseURL = "postgres://milton123:milton123@127.0.0.1:5432/lexiqa?sslmode=disable"
	}

	uploadDir := os.Getenv("UPLOAD_DIR")
	if uploadDir == "" {
		uploadDir = "./uploads"
	}

	log.Printf("[MAIN] Starting LEXIQA Server on port %s", port)
	log.Printf("[MAIN] Upload directory: %s", uploadDir)

	// 2. Initialize PostgreSQL Pool
	pool, err := db.InitDB(databaseURL)
	if err != nil {
		log.Fatalf("[FATAL] Database initialization failed: %v", err)
	}
	defer pool.Close()

	// 3. Setup Handlers
	syncHandler := &handlers.SyncHandler{
		DB: pool,
	}

	otaHandler := &handlers.OtaHandler{
		DB:        pool,
		UploadDir: uploadDir,
	}

	// Ensure uploads directories exist
	if err := otaHandler.EnsureUploadDirs(); err != nil {
		log.Fatalf("[FATAL] Failed to create upload directories: %v", err)
	}

	// 4. Register HTTP Endpoints (using Go 1.22+ ServeMux routing capabilities)
	mux := http.NewServeMux()

	// Middleware to log requests
	logMiddleware := func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			log.Printf("[HTTP] %s %s from %s", r.Method, r.URL.Path, r.RemoteAddr)
			next.ServeHTTP(w, r)
		})
	}

	// Synchronization endpoints
	mux.Handle("POST /v1/sync/batch", syncHandler)

	// OTA and Voice profile endpoints
	mux.HandleFunc("POST /v1/teachers/{id}/voice-samples", otaHandler.UploadVoiceSample)
	mux.HandleFunc("GET /v1/models/latest", otaHandler.GetLatestModel)
	mux.HandleFunc("GET /v1/models/{id}/download", otaHandler.DownloadModel)

	// Health check endpoint
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok","message":"LEXIQA Cloud Service matches H7 spec"}`))
	})

	// 5. Start Server
	serverAddr := ":" + port
	log.Printf("[MAIN] Server is listening at http://localhost%s", serverAddr)
	if err := http.ListenAndServe(serverAddr, logMiddleware(mux)); err != nil {
		log.Fatalf("[FATAL] HTTP server failed: %v", err)
	}
}
