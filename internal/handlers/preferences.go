// Package handlers contains the HTTP request handlers for the API.
package handlers

import (
	"encoding/json"
	"net/http"
	"strings"

	"github.com/MinnMinn/skills-introduction-to-github/internal/repository"
)

// PreferencesHandler groups the HTTP handlers for the preferences resource.
type PreferencesHandler struct {
	Repo *repository.PreferencesRepository
}

// ---------------------------------------------------------------------------
// Response / request shapes
// ---------------------------------------------------------------------------

// preferencesResponse is the JSON shape returned by GET and PUT.
type preferencesResponse struct {
	UserID        string `json:"user_id"`
	Theme         string `json:"theme"`
	Language      string `json:"language"`
	Notifications bool   `json:"notifications"`
	Timezone      string `json:"timezone"`
	UpdatedAt     string `json:"updated_at"`
}

// preferencesUpdateRequest is the JSON payload accepted by PUT.
// All fields are pointers so we can distinguish "not supplied" from
// the zero value (PATCH-style semantics).
type preferencesUpdateRequest struct {
	Theme         *string `json:"theme"`
	Language      *string `json:"language"`
	Notifications *bool   `json:"notifications"`
	Timezone      *string `json:"timezone"`
}

// ---------------------------------------------------------------------------
// GET /api/v1/preferences/{user_id}
// ---------------------------------------------------------------------------

// GetPreferences handles GET /api/v1/preferences/{user_id}.
func (h *PreferencesHandler) GetPreferences(w http.ResponseWriter, r *http.Request) {
	userID := r.PathValue("user_id")

	s, ok := h.Repo.Get(userID)
	if !ok {
		writeError(w, http.StatusNotFound, "User '"+userID+"' not found")
		return
	}

	writeJSON(w, http.StatusOK, preferencesResponse{
		UserID:        s.UserID,
		Theme:         s.Theme,
		Language:      s.Language,
		Notifications: s.Notifications,
		Timezone:      s.Timezone,
		UpdatedAt:     s.UpdatedAt.Format("2006-01-02T15:04:05.999999999Z07:00"),
	})
}

// ---------------------------------------------------------------------------
// PUT /api/v1/preferences/{user_id}
// ---------------------------------------------------------------------------

// UpdatePreferences handles PUT /api/v1/preferences/{user_id}.
func (h *PreferencesHandler) UpdatePreferences(w http.ResponseWriter, r *http.Request) {
	userID := r.PathValue("user_id")

	var payload preferencesUpdateRequest
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeValidationError(w, "body", "invalid JSON: "+err.Error())
		return
	}

	// Validate and collect non-nil fields
	fields := make(map[string]interface{})
	var validationErrors []validationDetail

	if payload.Theme != nil {
		v := *payload.Theme
		if v != "light" && v != "dark" {
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "theme"},
				Msg:  "Input should be 'light' or 'dark'",
				Type: "enum",
			})
		} else {
			fields["theme"] = v
		}
	}

	if payload.Language != nil {
		v := *payload.Language
		if strings.TrimSpace(v) == "" {
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "language"},
				Msg:  "language must not be blank",
				Type: "string_pattern_mismatch",
			})
		} else {
			fields["language"] = v
		}
	}

	if payload.Notifications != nil {
		fields["notifications"] = *payload.Notifications
	}

	if payload.Timezone != nil {
		v := *payload.Timezone
		if strings.TrimSpace(v) == "" {
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "timezone"},
				Msg:  "timezone must not be blank",
				Type: "string_pattern_mismatch",
			})
		} else {
			fields["timezone"] = v
		}
	}

	if len(validationErrors) > 0 {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]interface{}{
			"detail": validationErrors,
		})
		return
	}

	if len(fields) == 0 {
		writeValidationError(w, "body", "Request body must contain at least one field to update")
		return
	}

	s, err := h.Repo.UpdateFields(userID, fields)
	if err != nil {
		writeError(w, http.StatusUnprocessableEntity, err.Error())
		return
	}
	if s == nil {
		writeError(w, http.StatusNotFound, "User '"+userID+"' not found")
		return
	}

	writeJSON(w, http.StatusOK, preferencesResponse{
		UserID:        s.UserID,
		Theme:         s.Theme,
		Language:      s.Language,
		Notifications: s.Notifications,
		Timezone:      s.Timezone,
		UpdatedAt:     s.UpdatedAt.Format("2006-01-02T15:04:05.999999999Z07:00"),
	})
}
