// Package main is the application entry-point.
//
// It wires together the repositories, handlers, and HTTP router, then starts
// the server.  The default listening address is :8080 but can be overridden
// with the PORT environment variable.
package main

import (
	"log"
	"net/http"
	"os"

	"github.com/MinnMinn/skills-introduction-to-github/internal/handlers"
	"github.com/MinnMinn/skills-introduction-to-github/internal/repository"
)

func main() {
	// Repositories
	prefsRepo := repository.NewPreferencesRepository()
	ordersRepo := repository.NewOrdersRepository()

	// Handlers
	prefsH := &handlers.PreferencesHandler{Repo: prefsRepo}
	ordersH := &handlers.OrdersHandler{Repo: ordersRepo}

	mux := buildMux(prefsH, ordersH)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("User Preferences API v1.0.0 listening on :%s", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

// buildMux constructs and returns the application router.
// Extracted so that tests can call it directly without starting a real server.
func buildMux(prefsH *handlers.PreferencesHandler, ordersH *handlers.OrdersHandler) *http.ServeMux {
	mux := http.NewServeMux()

	// Liveness probe
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})

	// Preferences
	mux.HandleFunc("GET /api/v1/preferences/{user_id}", prefsH.GetPreferences)
	mux.HandleFunc("PUT /api/v1/preferences/{user_id}", prefsH.UpdatePreferences)

	// Orders
	mux.HandleFunc("POST /api/v1/orders", ordersH.CreateOrder)

	return mux
}
