package handlers

import (
	"encoding/json"
	"net/http"
)

// validationDetail mirrors the FastAPI / Pydantic error shape so that
// clients receive consistent, field-level error information.
type validationDetail struct {
	Loc  []interface{} `json:"loc"`
	Msg  string        `json:"msg"`
	Type string        `json:"type"`
}

// errorResponse is the shape used for 4xx responses.
type errorResponse struct {
	Detail string `json:"detail"`
}

// writeJSON serialises v as JSON and writes it to w with the given status code.
func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// writeError writes a simple {"detail": msg} JSON error response.
func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Detail: msg})
}

// writeValidationError writes a 422 response with a single validation detail.
func writeValidationError(w http.ResponseWriter, field, msg string) {
	writeJSON(w, http.StatusUnprocessableEntity, map[string]interface{}{
		"detail": []validationDetail{
			{
				Loc:  []interface{}{"body", field},
				Msg:  msg,
				Type: "value_error",
			},
		},
	})
}
