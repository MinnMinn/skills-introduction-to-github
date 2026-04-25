// User Preferences API — Go port of the Python/FastAPI service.
//
// Routes:
//
//	GET  /health
//	GET  /api/v1/preferences/{user_id}
//	PUT  /api/v1/preferences/{user_id}
//	POST /api/v1/orders
package main

import (
	"log"
	"net/http"

	"github.com/MinnMinn/skills-introduction-to-github/api"
	"github.com/MinnMinn/skills-introduction-to-github/db"
)

func main() {
	mux := buildMux(
		db.NewPreferencesRepository(),
		db.NewOrdersRepository(),
	)

	addr := ":8080"
	log.Printf("User Preferences API listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

// buildMux wires up all routes and returns the ServeMux.
// Extracted so tests can create an isolated mux with their own repositories.
func buildMux(
	prefRepo *db.PreferencesRepository,
	ordersRepo *db.OrdersRepository,
) *http.ServeMux {
	mux := http.NewServeMux()

	// Health check
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})

	// Preferences
	mux.Handle("/api/v1/preferences/", api.NewPreferencesHandler(prefRepo))

	// Orders
	mux.Handle("/api/v1/orders", api.NewOrdersHandler(ordersRepo))

	return mux
}
