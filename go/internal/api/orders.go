package api

import (
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"regexp"
	"strconv"

	"github.com/MinnMinn/skills-introduction-to-github/internal/db"
	"github.com/MinnMinn/skills-introduction-to-github/internal/schemas"
)

// uuidRegex matches a UUID v4 (case-insensitive).
var uuidRegex = regexp.MustCompile(
	`(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`,
)

// OrdersHandler groups the HTTP handlers for the orders resource.
type OrdersHandler struct {
	repo *db.OrdersRepository
}

// NewOrdersHandler returns a handler backed by repo.
func NewOrdersHandler(repo *db.OrdersRepository) *OrdersHandler {
	return &OrdersHandler{repo: repo}
}

// RegisterRoutes wires the handler methods into mux under the given prefix.
//
//	POST {prefix}
func (h *OrdersHandler) RegisterRoutes(mux *http.ServeMux, prefix string) {
	mux.HandleFunc(fmt.Sprintf("POST %s", prefix), h.createOrder)
}

// ---------------------------------------------------------------------------
// POST /api/v1/orders
// ---------------------------------------------------------------------------

// rawOrderPayload is used to decode the request body before type validation.
// We use json.RawMessage for fields so we can distinguish missing from zero.
type rawOrderPayload struct {
	ProductID *json.RawMessage `json:"product_id"`
	Quantity  *json.RawMessage `json:"quantity"`
	Price     *json.RawMessage `json:"price"`
}

func (h *OrdersHandler) createOrder(w http.ResponseWriter, r *http.Request) {
	// Decode into a raw map so we can provide field-level 422 errors.
	var raw rawOrderPayload
	if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
		writeValidationError(w, []string{"body"}, "invalid JSON body", "json_invalid")
		return
	}

	// --- product_id ---
	if raw.ProductID == nil {
		writeValidationError(w, []string{"body", "product_id"}, "field required", "missing")
		return
	}
	var productIDStr string
	if err := json.Unmarshal(*raw.ProductID, &productIDStr); err != nil {
		// Could be a non-string type
		writeValidationError(w, []string{"body", "product_id"}, "value is not a valid uuid", "uuid_parsing")
		return
	}
	if !uuidRegex.MatchString(productIDStr) {
		writeValidationError(w, []string{"body", "product_id"}, "value is not a valid uuid", "uuid_parsing")
		return
	}

	// --- quantity ---
	if raw.Quantity == nil {
		writeValidationError(w, []string{"body", "quantity"}, "field required", "missing")
		return
	}
	// Parse as a float64 first so we can reject fractional values.
	var quantityFloat float64
	if err := json.Unmarshal(*raw.Quantity, &quantityFloat); err != nil {
		writeValidationError(w, []string{"body", "quantity"}, "value is not a valid integer", "int_parsing")
		return
	}
	// Reject non-integer floats (e.g. 1.5)
	if quantityFloat != math.Trunc(quantityFloat) {
		writeValidationError(w, []string{"body", "quantity"}, "value is not a valid integer", "int_parsing")
		return
	}
	quantity := int(quantityFloat)
	if quantity <= 0 {
		writeValidationError(w, []string{"body", "quantity"}, "ensure this value is greater than 0", "greater_than")
		return
	}

	// --- price ---
	if raw.Price == nil {
		writeValidationError(w, []string{"body", "price"}, "field required", "missing")
		return
	}
	var priceFloat float64
	if err := json.Unmarshal(*raw.Price, &priceFloat); err != nil {
		// Try parsing as a string (e.g. "9.99")
		var priceStr string
		if jsonErr := json.Unmarshal(*raw.Price, &priceStr); jsonErr != nil {
			writeValidationError(w, []string{"body", "price"}, "value is not a valid decimal", "decimal_parsing")
			return
		}
		parsed, parseErr := strconv.ParseFloat(priceStr, 64)
		if parseErr != nil {
			writeValidationError(w, []string{"body", "price"}, "value is not a valid decimal", "decimal_parsing")
			return
		}
		priceFloat = parsed
	}
	if priceFloat < 0.01 {
		writeValidationError(w, []string{"body", "price"}, "ensure this value is greater than or equal to 0.01", "greater_than_equal")
		return
	}
	// Format the price as a decimal string (preserve up to 10 significant digits)
	priceStr := strconv.FormatFloat(priceFloat, 'f', -1, 64)

	// All validation passed — create the order.
	order, err := h.repo.CreateOrder(productIDStr, quantity, priceStr)
	if err != nil {
		http.Error(w, "internal server error", http.StatusInternalServerError)
		return
	}

	writeJSON(w, http.StatusCreated, schemas.OrderResponse{
		OrderID:   order.OrderID,
		ProductID: order.ProductID,
		Quantity:  order.Quantity,
		Price:     order.Price,
		Status:    order.Status,
		CreatedAt: order.CreatedAt,
	})
}
