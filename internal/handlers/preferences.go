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
// Response shape
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
//
// All fields are optional (PATCH-style semantics over PUT).  At least one
// field must be supplied.  The handler validates values before persisting.
func (h *PreferencesHandler) UpdatePreferences(w http.ResponseWriter, r *http.Request) {
	userID := r.PathValue("user_id")

	// Decode into a raw map so that we can distinguish missing keys from
	// explicit null / wrong-type values.
	var raw map[string]json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
		writeValidationError(w, "body", "invalid JSON: "+err.Error())
		return
	}

	var validationErrors []validationDetail
	fields := make(map[string]interface{})

	// ---- theme -------------------------------------------------------
	if rawTheme, ok := raw["theme"]; ok {
		var v interface{}
		_ = json.Unmarshal(rawTheme, &v)
		sv, isStr := v.(string)
		if !isStr {
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "theme"},
				Msg:  "Input should be a string",
				Type: "string_type",
			})
		} else if sv != "light" && sv != "dark" {
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "theme"},
				Msg:  "Input should be 'light' or 'dark'",
				Type: "enum",
			})
		} else {
			fields["theme"] = sv
		}
	}

	// ---- language ----------------------------------------------------
	if rawLang, ok := raw["language"]; ok {
		var v interface{}
		_ = json.Unmarshal(rawLang, &v)
		sv, isStr := v.(string)
		if !isStr {
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "language"},
				Msg:  "Input should be a string",
				Type: "string_type",
			})
		} else if strings.TrimSpace(sv) == "" {
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "language"},
				Msg:  "language must not be blank",
				Type: "string_pattern_mismatch",
			})
		} else {
			fields["language"] = sv
		}
	}

	// ---- notifications -----------------------------------------------
	if rawNotif, ok := raw["notifications"]; ok {
		var v interface{}
		_ = json.Unmarshal(rawNotif, &v)
		bv, isBool := v.(bool)
		if !isBool {
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "notifications"},
				Msg:  "Input should be a valid boolean",
				Type: "bool_parsing",
			})
		} else {
			fields["notifications"] = bv
		}
	}

	// ---- timezone ----------------------------------------------------
	if rawTZ, ok := raw["timezone"]; ok {
		var v interface{}
		_ = json.Unmarshal(rawTZ, &v)
		sv, isStr := v.(string)
		if !isStr {
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "timezone"},
				Msg:  "Input should be a string",
				Type: "string_type",
			})
		} else if strings.TrimSpace(sv) == "" {
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "timezone"},
				Msg:  "timezone must not be blank",
				Type: "string_pattern_mismatch",
			})
		} else {
			fields["timezone"] = sv
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
