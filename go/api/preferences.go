package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/MinnMinn/skills-introduction-to-github/db"
)

// PreferencesHandler handles all routes under /api/v1/preferences/.
type PreferencesHandler struct {
	repo *db.PreferencesRepository
}

// NewPreferencesHandler creates a handler wired to the given repository.
func NewPreferencesHandler(repo *db.PreferencesRepository) *PreferencesHandler {
	return &PreferencesHandler{repo: repo}
}

// ServeHTTP dispatches GET and PUT on /api/v1/preferences/{user_id}.
func (h *PreferencesHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// Extract {user_id} — the path is /api/v1/preferences/{user_id}
	userID := strings.TrimPrefix(r.URL.Path, "/api/v1/preferences/")
	if userID == "" || userID == "/" {
		writeError(w, http.StatusBadRequest, "user_id is required")
		return
	}
	// Strip any trailing slash
	userID = strings.TrimSuffix(userID, "/")

	switch r.Method {
	case http.MethodGet:
		h.getPreferences(w, r, userID)
	case http.MethodPut:
		h.updatePreferences(w, r, userID)
	default:
		writeError(w, http.StatusMethodNotAllowed, fmt.Sprintf("method %s not allowed", r.Method))
	}
}

// ---------------------------------------------------------------------------
// GET /api/v1/preferences/{user_id}
// ---------------------------------------------------------------------------

func (h *PreferencesHandler) getPreferences(w http.ResponseWriter, _ *http.Request, userID string) {
	record := h.repo.Get(userID)
	if record == nil {
		writeError(w, http.StatusNotFound, fmt.Sprintf("User '%s' not found", userID))
		return
	}
	writeJSON(w, http.StatusOK, record)
}

// ---------------------------------------------------------------------------
// PUT /api/v1/preferences/{user_id}
// ---------------------------------------------------------------------------

// preferencesUpdateRequest is the JSON body accepted by PUT.
// Pointer fields allow distinguishing "absent" from zero-value.
type preferencesUpdateRequest struct {
	Theme         *string `json:"theme"`
	Language      *string `json:"language"`
	Notifications *bool   `json:"notifications"`
	Timezone      *string `json:"timezone"`
}

func (h *PreferencesHandler) updatePreferences(w http.ResponseWriter, r *http.Request, userID string) {
	var payload preferencesUpdateRequest
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeValidationError(w, "body", "invalid JSON")
		return
	}

	// At least one field must be present.
	if payload.Theme == nil && payload.Language == nil &&
		payload.Notifications == nil && payload.Timezone == nil {
		writeError(w, http.StatusUnprocessableEntity,
			"Request body must contain at least one field to update")
		return
	}

	// Validate theme.
	if payload.Theme != nil {
		t := *payload.Theme
		if t != "light" && t != "dark" {
			writeValidationError(w, "theme", "theme must be 'light' or 'dark'")
			return
		}
	}

	// Validate language (non-blank when supplied).
	if payload.Language != nil && strings.TrimSpace(*payload.Language) == "" {
		writeValidationError(w, "language", "language must not be blank")
		return
	}

	// Validate timezone (non-blank when supplied).
	if payload.Timezone != nil && strings.TrimSpace(*payload.Timezone) == "" {
		writeValidationError(w, "timezone", "timezone must not be blank")
		return
	}

	fields := db.PreferencesFields{
		Theme:         payload.Theme,
		Language:      payload.Language,
		Notifications: payload.Notifications,
		Timezone:      payload.Timezone,
	}

	record, err := h.repo.Update(userID, fields)
	if err != nil {
		writeError(w, http.StatusUnprocessableEntity, err.Error())
		return
	}
	if record == nil {
		writeError(w, http.StatusNotFound, fmt.Sprintf("User '%s' not found", userID))
		return
	}

	writeJSON(w, http.StatusOK, record)
}
