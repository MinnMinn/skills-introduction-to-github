// main is the application entry-point.
//
// It wires together all API handlers, mounts them on a single ServeMux, and
// starts the HTTP server. The server listens on the address controlled by the
// PORT environment variable (default: 8080).
package main

import (
	"log"
	"net/http"
	"os"

	"github.com/MinnMinn/skills-introduction-to-github/internal/api"
	"github.com/MinnMinn/skills-introduction-to-github/internal/db"
)

func main() {
	mux := NewRouter()

	addr := ":" + port()
	log.Printf("User Preferences API listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

// NewRouter builds and returns the application ServeMux.
// Extracted so tests can call it directly without starting a real listener.
func NewRouter() *http.ServeMux {
	mux := http.NewServeMux()

	// Repositories
	prefsRepo := db.NewPreferencesRepository()
	ordersRepo := db.NewOrdersRepository()

	// Handlers
	prefsHandler := api.NewPreferencesHandler(prefsRepo)
	ordersHandler := api.NewOrdersHandler(ordersRepo)

	// Routes
	prefsHandler.RegisterRoutes(mux, "/api/v1/preferences")
	ordersHandler.RegisterRoutes(mux, "/api/v1/orders")

	// Health check
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"ok"}` + "\n"))
	})

	return mux
}

// port returns the server port from the PORT env var, defaulting to "8080".
func port() string {
	if p := os.Getenv("PORT"); p != "" {
		return p
	}
	return "8080"
}
