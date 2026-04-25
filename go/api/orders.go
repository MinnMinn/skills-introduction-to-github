package api

import (
	"encoding/json"
	"fmt"
	"math/big"
	"net/http"
	"regexp"
	"strings"

	"github.com/MinnMinn/skills-introduction-to-github/db"
)

// uuidV4Re matches a canonical UUID v4 string (case-insensitive).
var uuidV4Re = regexp.MustCompile(
	`(?i)^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`,
)

// OrdersHandler handles all routes under /api/v1/orders.
type OrdersHandler struct {
	repo *db.OrdersRepository
}

// NewOrdersHandler creates a handler wired to the given repository.
func NewOrdersHandler(repo *db.OrdersRepository) *OrdersHandler {
	return &OrdersHandler{repo: repo}
}

// ServeHTTP dispatches POST on /api/v1/orders.
func (h *OrdersHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, fmt.Sprintf("method %s not allowed", r.Method))
		return
	}
	h.createOrder(w, r)
}

// ---------------------------------------------------------------------------
// POST /api/v1/orders
// ---------------------------------------------------------------------------

// orderCreateRequest is the JSON body accepted by POST /api/v1/orders.
// We use interface{} for product_id and price so we can reject wrong types
// before attempting further conversion.
type orderCreateRequest struct {
	ProductID interface{} `json:"product_id"`
	Quantity  interface{} `json:"quantity"`
	Price     interface{} `json:"price"`
}

func (h *OrdersHandler) createOrder(w http.ResponseWriter, r *http.Request) {
	var raw orderCreateRequest
	if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
		writeValidationError(w, "body", "invalid JSON")
		return
	}

	// --- product_id ---
	if raw.ProductID == nil {
		writeValidationError(w, "product_id", "field required")
		return
	}
	productIDStr, ok := raw.ProductID.(string)
	if !ok {
		writeValidationError(w, "product_id", "product_id must be a UUID string")
		return
	}
	if !uuidV4Re.MatchString(strings.TrimSpace(productIDStr)) {
		writeValidationError(w, "product_id", "product_id must be a valid UUID v4")
		return
	}

	// --- quantity ---
	if raw.Quantity == nil {
		writeValidationError(w, "quantity", "field required")
		return
	}
	// JSON numbers decode as float64 when using interface{}.
	quantityF, ok := raw.Quantity.(float64)
	if !ok {
		writeValidationError(w, "quantity", "quantity must be an integer")
		return
	}
	// Must be a whole number.
	if quantityF != float64(int(quantityF)) {
		writeValidationError(w, "quantity", "quantity must be an integer")
		return
	}
	quantity := int(quantityF)
	if quantity <= 0 {
		writeValidationError(w, "quantity", "quantity must be greater than 0")
		return
	}

	// --- price ---
	if raw.Price == nil {
		writeValidationError(w, "price", "field required")
		return
	}
	// Accept both number and string representations of the price.
	var priceStr string
	switch v := raw.Price.(type) {
	case string:
		priceStr = v
	case float64:
		priceStr = fmt.Sprintf("%g", v)
	default:
		writeValidationError(w, "price", "price must be a decimal number")
		return
	}
	priceVal, _, err := big.ParseFloat(priceStr, 10, 64, big.ToNearestEven)
	if err != nil || priceVal.Sign() < 0 {
		writeValidationError(w, "price", "price must be a valid decimal number")
		return
	}
	minPrice, _, _ := big.ParseFloat("0.01", 10, 64, big.ToNearestEven)
	if priceVal.Cmp(minPrice) < 0 {
		writeValidationError(w, "price", "price must be >= 0.01")
		return
	}

	order, err := h.repo.CreateOrder(productIDStr, quantity, priceStr)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create order")
		return
	}

	writeJSON(w, http.StatusCreated, order)
}
