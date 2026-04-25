package api

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/MinnMinn/skills-introduction-to-github/internal/db"
	"github.com/MinnMinn/skills-introduction-to-github/internal/schemas"
)

// PreferencesHandler groups the HTTP handlers for the preferences resource.
// It holds a reference to the repository so that tests can inject a fake.
type PreferencesHandler struct {
	repo *db.PreferencesRepository
}

// NewPreferencesHandler returns a handler backed by repo.
func NewPreferencesHandler(repo *db.PreferencesRepository) *PreferencesHandler {
	return &PreferencesHandler{repo: repo}
}

// RegisterRoutes wires the handler methods into mux under the given prefix.
//
//	GET  {prefix}/{user_id}
//	PUT  {prefix}/{user_id}
func (h *PreferencesHandler) RegisterRoutes(mux *http.ServeMux, prefix string) {
	// Go 1.22 ServeMux supports "{method} {pattern}" routing.
	mux.HandleFunc(fmt.Sprintf("GET %s/{user_id}", prefix), h.getPreferences)
	mux.HandleFunc(fmt.Sprintf("PUT %s/{user_id}", prefix), h.updatePreferences)
}

// ---------------------------------------------------------------------------
// GET /api/v1/preferences/{user_id}
// ---------------------------------------------------------------------------

func (h *PreferencesHandler) getPreferences(w http.ResponseWriter, r *http.Request) {
	userID := r.PathValue("user_id")

	record := h.repo.Get(userID)
	if record == nil {
		writeError(w, http.StatusNotFound, fmt.Sprintf("User '%s' not found", userID))
		return
	}

	writeJSON(w, http.StatusOK, schemas.PreferencesResponse{
		UserID:        record.UserID,
		Theme:         record.Theme,
		Language:      record.Language,
		Notifications: record.Notifications,
		Timezone:      record.Timezone,
		UpdatedAt:     record.UpdatedAt,
	})
}

// ---------------------------------------------------------------------------
// PUT /api/v1/preferences/{user_id}
// ---------------------------------------------------------------------------

func (h *PreferencesHandler) updatePreferences(w http.ResponseWriter, r *http.Request) {
	userID := r.PathValue("user_id")

	var payload schemas.PreferencesUpdateRequest
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeValidationError(w, []string{"body"}, "invalid JSON body", "json_invalid")
		return
	}

	if err := payload.Validate(); err != nil {
		writeValidationError(w, []string{"body"}, err.Error(), "value_error")
		return
	}

	// Build the fields map from only the non-nil fields.
	fields := make(map[string]interface{})
	if payload.Theme != nil {
		fields["theme"] = *payload.Theme
	}
	if payload.Language != nil {
		fields["language"] = *payload.Language
	}
	if payload.Notifications != nil {
		fields["notifications"] = *payload.Notifications
	}
	if payload.Timezone != nil {
		fields["timezone"] = *payload.Timezone
	}

	record, err := h.repo.Update(userID, fields)
	if err != nil {
		writeValidationError(w, []string{"body"}, err.Error(), "value_error")
		return
	}
	if record == nil {
		writeError(w, http.StatusNotFound, fmt.Sprintf("User '%s' not found", userID))
		return
	}

	writeJSON(w, http.StatusOK, schemas.PreferencesResponse{
		UserID:        record.UserID,
		Theme:         record.Theme,
		Language:      record.Language,
		Notifications: record.Notifications,
		Timezone:      record.Timezone,
		UpdatedAt:     record.UpdatedAt,
	})
}
