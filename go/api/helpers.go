// Package api contains all HTTP handler functions and routing helpers.
package api

import (
	"encoding/json"
	"net/http"
)

// writeJSON serialises v as JSON and writes it to w with the given status code.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// writeError writes a JSON error body consistent with the FastAPI `detail`
// envelope, e.g. {"detail": "User 'x' not found"}.
func writeError(w http.ResponseWriter, status int, detail string) {
	writeJSON(w, status, map[string]string{"detail": detail})
}

// writeValidationError writes a 422 response with a `detail` list that
// mirrors FastAPI's validation-error shape, making client responses
// structurally compatible.
//
//	{"detail": [{"loc": ["body", field], "msg": msg, "type": "value_error"}]}
func writeValidationError(w http.ResponseWriter, field, msg string) {
	type valErr struct {
		Loc  []string `json:"loc"`
		Msg  string   `json:"msg"`
		Type string   `json:"type"`
	}
	body := map[string][]valErr{
		"detail": {
			{Loc: []string{"body", field}, Msg: msg, Type: "value_error"},
		},
	}
	writeJSON(w, http.StatusUnprocessableEntity, body)
}
