// Package api contains the HTTP handlers for all API endpoints.
package api

import (
	"encoding/json"
	"net/http"

	"github.com/MinnMinn/skills-introduction-to-github/internal/schemas"
)

// writeJSON serialises v as JSON and writes it to w with the given HTTP status.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// writeError writes a simple {"detail": msg} JSON error with the given status.
func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, schemas.SimpleErrorResponse{Detail: msg})
}

// writeValidationError writes a FastAPI-compatible 422 body with one entry.
func writeValidationError(w http.ResponseWriter, loc []string, msg, errType string) {
	body := schemas.ValidationErrorResponse{
		Detail: []schemas.ErrorDetail{
			{Loc: loc, Msg: msg, Type: errType},
		},
	}
	writeJSON(w, http.StatusUnprocessableEntity, body)
}
