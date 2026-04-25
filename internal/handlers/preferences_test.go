package handlers_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/MinnMinn/skills-introduction-to-github/internal/handlers"
	"github.com/MinnMinn/skills-introduction-to-github/internal/models"
	"github.com/MinnMinn/skills-introduction-to-github/internal/repository"
)

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

func newPrefsHandler() (*handlers.PreferencesHandler, *repository.PreferencesRepository) {
	repo := repository.NewPreferencesRepository()
	return &handlers.PreferencesHandler{Repo: repo}, repo
}

func seedUser(repo *repository.PreferencesRepository) {
	s := models.NewUserSettings("user-123")
	s.Theme = "light"
	s.Language = "en"
	s.Notifications = true
	s.Timezone = "UTC"
	repo.Seed(s)
}

func doPrefsGET(t *testing.T, h *handlers.PreferencesHandler, userID string) *httptest.ResponseRecorder {
	t.Helper()
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/v1/preferences/{user_id}", h.GetPreferences)
	req := httptest.NewRequest(http.MethodGet, "/api/v1/preferences/"+userID, nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	return w
}

func doPrefsPUT(t *testing.T, h *handlers.PreferencesHandler, userID string, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	mux := http.NewServeMux()
	mux.HandleFunc("PUT /api/v1/preferences/{user_id}", h.UpdatePreferences)
	b, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPut, "/api/v1/preferences/"+userID, bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	return w
}

// ---------------------------------------------------------------------------
// GET — happy path
// ---------------------------------------------------------------------------

func TestGetPreferences_Returns200WithCorrectPayload(t *testing.T) {
	h, repo := newPrefsHandler()
	seedUser(repo)

	w := doPrefsGET(t, h, "user-123")

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)

	if body["user_id"] != "user-123" {
		t.Errorf("unexpected user_id: %v", body["user_id"])
	}
	if body["theme"] != "light" {
		t.Errorf("unexpected theme: %v", body["theme"])
	}
	if body["language"] != "en" {
		t.Errorf("unexpected language: %v", body["language"])
	}
	if body["notifications"] != true {
		t.Errorf("unexpected notifications: %v", body["notifications"])
	}
	if body["timezone"] != "UTC" {
		t.Errorf("unexpected timezone: %v", body["timezone"])
	}
	if _, ok := body["updated_at"]; !ok {
		t.Error("expected updated_at key in response")
	}
}

func TestGetPreferences_ResponseContainsAllExpectedKeys(t *testing.T) {
	h, repo := newPrefsHandler()
	seedUser(repo)

	w := doPrefsGET(t, h, "user-123")

	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)
	expected := []string{"user_id", "theme", "language", "notifications", "timezone", "updated_at"}
	for _, k := range expected {
		if _, ok := body[k]; !ok {
			t.Errorf("missing key: %s", k)
		}
	}
}

// ---------------------------------------------------------------------------
// GET — not found
// ---------------------------------------------------------------------------

func TestGetPreferences_Returns404ForUnknownUser(t *testing.T) {
	h, _ := newPrefsHandler()

	w := doPrefsGET(t, h, "ghost-user")

	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)
	detail, _ := body["detail"].(string)
	if detail == "" {
		t.Error("expected non-empty detail in 404 response")
	}
}

// ---------------------------------------------------------------------------
// PUT — happy path (full payload)
// ---------------------------------------------------------------------------

func TestUpdatePreferences_Returns200WithUpdatedValues(t *testing.T) {
	h, repo := newPrefsHandler()
	seedUser(repo)

	payload := map[string]interface{}{
		"theme": "dark", "language": "fr", "notifications": false, "timezone": "Europe/Paris",
	}
	w := doPrefsPUT(t, h, "user-123", payload)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)
	if body["theme"] != "dark" {
		t.Errorf("unexpected theme: %v", body["theme"])
	}
	if body["language"] != "fr" {
		t.Errorf("unexpected language: %v", body["language"])
	}
	if body["notifications"] != false {
		t.Errorf("unexpected notifications: %v", body["notifications"])
	}
	if body["timezone"] != "Europe/Paris" {
		t.Errorf("unexpected timezone: %v", body["timezone"])
	}
}

// ---------------------------------------------------------------------------
// PUT — happy path (partial payload)
// ---------------------------------------------------------------------------

func TestUpdatePreferences_OnlySuppliedFieldsAreChanged(t *testing.T) {
	h, repo := newPrefsHandler()
	seedUser(repo)

	w := doPrefsPUT(t, h, "user-123", map[string]interface{}{"theme": "dark"})

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)
	if body["theme"] != "dark" {
		t.Errorf("expected theme=dark, got %v", body["theme"])
	}
	if body["language"] != "en" {
		t.Errorf("expected language unchanged (en), got %v", body["language"])
	}
	if body["notifications"] != true {
		t.Errorf("expected notifications unchanged (true), got %v", body["notifications"])
	}
	if body["timezone"] != "UTC" {
		t.Errorf("expected timezone unchanged (UTC), got %v", body["timezone"])
	}
}

// ---------------------------------------------------------------------------
// PUT — not found
// ---------------------------------------------------------------------------

func TestUpdatePreferences_Returns404ForUnknownUser(t *testing.T) {
	h, _ := newPrefsHandler()

	w := doPrefsPUT(t, h, "no-such-user", map[string]interface{}{"theme": "dark"})

	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

// ---------------------------------------------------------------------------
// PUT — validation errors (422)
// ---------------------------------------------------------------------------

func TestUpdatePreferences_InvalidThemeReturns422(t *testing.T) {
	h, repo := newPrefsHandler()
	seedUser(repo)

	w := doPrefsPUT(t, h, "user-123", map[string]interface{}{"theme": "rainbow"})

	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestUpdatePreferences_BlankLanguageReturns422(t *testing.T) {
	h, repo := newPrefsHandler()
	seedUser(repo)

	w := doPrefsPUT(t, h, "user-123", map[string]interface{}{"language": "   "})

	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestUpdatePreferences_BlankTimezoneReturns422(t *testing.T) {
	h, repo := newPrefsHandler()
	seedUser(repo)

	w := doPrefsPUT(t, h, "user-123", map[string]interface{}{"timezone": ""})

	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestUpdatePreferences_EmptyBodyReturns422(t *testing.T) {
	h, repo := newPrefsHandler()
	seedUser(repo)

	w := doPrefsPUT(t, h, "user-123", map[string]interface{}{})

	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestUpdatePreferences_WrongTypeForNotificationsReturns422(t *testing.T) {
	h, repo := newPrefsHandler()
	seedUser(repo)

	// JSON with string for notifications field — will be decoded as string, not bool
	raw := `{"notifications": "yes_please"}`
	mux := http.NewServeMux()
	mux.HandleFunc("PUT /api/v1/preferences/{user_id}", h.UpdatePreferences)
	req := httptest.NewRequest(http.MethodPut, "/api/v1/preferences/user-123", bytes.NewBufferString(raw))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422 for wrong notifications type, got %d: %s", w.Code, w.Body.String())
	}
}
