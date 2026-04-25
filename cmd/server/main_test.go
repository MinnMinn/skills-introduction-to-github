package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/MinnMinn/skills-introduction-to-github/internal/handlers"
	"github.com/MinnMinn/skills-introduction-to-github/internal/repository"
)

func TestHealthEndpoint(t *testing.T) {
	prefsH := &handlers.PreferencesHandler{Repo: repository.NewPreferencesRepository()}
	ordersH := &handlers.OrdersHandler{Repo: repository.NewOrdersRepository()}
	mux := buildMux(prefsH, ordersH)

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}

	var body map[string]interface{}
	if err := json.NewDecoder(w.Body).Decode(&body); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if body["status"] != "ok" {
		t.Errorf("expected status=ok, got %v", body["status"])
	}
}
