// Package schemas contains request/response DTOs and their validation logic.
// Each type mirrors the Pydantic models from the original Python service.
//
// Sections:
//   - Preferences API  (PreferencesResponse, PreferencesUpdateRequest)
//   - Orders API       (OrderCreateRequest, OrderResponse)
package schemas

import (
	"fmt"
	"strings"
)

// ---------------------------------------------------------------------------
// Preferences — Response schema
// ---------------------------------------------------------------------------

// PreferencesResponse is the full preferences object returned by GET and PUT.
type PreferencesResponse struct {
	UserID        string `json:"user_id"`
	Theme         string `json:"theme"`
	Language      string `json:"language"`
	Notifications bool   `json:"notifications"`
	Timezone      string `json:"timezone"`
	UpdatedAt     string `json:"updated_at"`
}

// ---------------------------------------------------------------------------
// Preferences — Request schema (partial update — all fields optional)
// ---------------------------------------------------------------------------

// PreferencesUpdateRequest is the payload accepted by
// PUT /api/v1/preferences/{user_id}.
//
// All fields are optional so that callers can perform a partial update
// (PATCH-style semantics over PUT). At least one field must be present.
//
// Pointer fields distinguish "not supplied" (nil) from a supplied zero value.
type PreferencesUpdateRequest struct {
	Theme         *string `json:"theme"`
	Language      *string `json:"language"`
	Notifications *bool   `json:"notifications"`
	Timezone      *string `json:"timezone"`
}

// HasUpdates returns true if at least one field was supplied.
func (r *PreferencesUpdateRequest) HasUpdates() bool {
	return r.Theme != nil || r.Language != nil ||
		r.Notifications != nil || r.Timezone != nil
}

// Validate checks field-level business rules.
// Returns a non-nil error whose message is safe to surface to callers.
func (r *PreferencesUpdateRequest) Validate() error {
	if !r.HasUpdates() {
		return fmt.Errorf("request body must contain at least one field to update")
	}
	if r.Theme != nil {
		if *r.Theme != "light" && *r.Theme != "dark" {
			return fmt.Errorf("theme must be 'light' or 'dark'")
		}
	}
	if r.Language != nil {
		if strings.TrimSpace(*r.Language) == "" {
			return fmt.Errorf("language must not be blank")
		}
	}
	if r.Timezone != nil {
		if strings.TrimSpace(*r.Timezone) == "" {
			return fmt.Errorf("timezone must not be blank")
		}
	}
	return nil
}

// ---------------------------------------------------------------------------
// Orders — Request schema
// ---------------------------------------------------------------------------

// OrderCreateRequest is the payload accepted by POST /api/v1/orders.
//
// Validation rules:
//   - product_id : must be a valid UUID v4 string
//   - quantity   : integer strictly greater than 0
//   - price      : decimal string with numeric value >= 0.01
type OrderCreateRequest struct {
	ProductID *string  `json:"product_id"`
	Quantity  *int     `json:"quantity"`
	Price     *float64 `json:"price"`
}

// ---------------------------------------------------------------------------
// Orders — Response schema
// ---------------------------------------------------------------------------

// OrderResponse is the order object returned after a successful creation.
type OrderResponse struct {
	OrderID   string `json:"order_id"`
	ProductID string `json:"product_id"`
	Quantity  int    `json:"quantity"`
	Price     string `json:"price"`
	Status    string `json:"status"`
	CreatedAt string `json:"created_at"`
}

// ---------------------------------------------------------------------------
// Shared error response
// ---------------------------------------------------------------------------

// ErrorDetail mirrors FastAPI's 422 field-level error entry.
type ErrorDetail struct {
	Loc  []string `json:"loc"`
	Msg  string   `json:"msg"`
	Type string   `json:"type"`
}

// ValidationErrorResponse mirrors FastAPI's 422 body.
type ValidationErrorResponse struct {
	Detail []ErrorDetail `json:"detail"`
}

// SimpleErrorResponse is used for 404 and other single-message errors.
type SimpleErrorResponse struct {
	Detail string `json:"detail"`
}
