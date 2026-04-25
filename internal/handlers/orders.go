package handlers

import (
	"encoding/json"
	"net/http"
	"regexp"
	"strconv"

	"github.com/MinnMinn/skills-introduction-to-github/internal/repository"
)

// uuidRegex matches a canonical UUID v4 (case-insensitive).
var uuidRegex = regexp.MustCompile(
	`(?i)^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`,
)

// OrdersHandler groups the HTTP handlers for the orders resource.
type OrdersHandler struct {
	Repo *repository.OrdersRepository
}

// ---------------------------------------------------------------------------
// Request / response shapes
// ---------------------------------------------------------------------------

// orderCreateRequest is the JSON payload accepted by POST /api/v1/orders.
type orderCreateRequest struct {
	ProductID *string      `json:"product_id"`
	Quantity  *json.Number `json:"quantity"`
	Price     *json.Number `json:"price"`
}

// orderResponse is the JSON shape returned after a successful order creation.
type orderResponse struct {
	OrderID   string `json:"order_id"`
	ProductID string `json:"product_id"`
	Quantity  int    `json:"quantity"`
	Price     string `json:"price"`
	Status    string `json:"status"`
	CreatedAt string `json:"created_at"`
}

// ---------------------------------------------------------------------------
// POST /api/v1/orders
// ---------------------------------------------------------------------------

// CreateOrder handles POST /api/v1/orders.
func (h *OrdersHandler) CreateOrder(w http.ResponseWriter, r *http.Request) {
	// Decode using a raw map first so we can tell missing fields from bad values.
	var raw map[string]json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
		writeValidationError(w, "body", "invalid JSON: "+err.Error())
		return
	}

	var validationErrors []validationDetail

	// ---- product_id --------------------------------------------------------
	var productID string
	if rawPID, ok := raw["product_id"]; !ok {
		validationErrors = append(validationErrors, validationDetail{
			Loc:  []interface{}{"body", "product_id"},
			Msg:  "Field required",
			Type: "missing",
		})
	} else {
		var pid interface{}
		_ = json.Unmarshal(rawPID, &pid)
		pidStr, isStr := pid.(string)
		if !isStr || !uuidRegex.MatchString(pidStr) {
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "product_id"},
				Msg:  "value is not a valid UUID",
				Type: "uuid_parsing",
			})
		} else {
			productID = pidStr
		}
	}

	// ---- quantity ----------------------------------------------------------
	var quantity int
	if rawQty, ok := raw["quantity"]; !ok {
		validationErrors = append(validationErrors, validationDetail{
			Loc:  []interface{}{"body", "quantity"},
			Msg:  "Field required",
			Type: "missing",
		})
	} else {
		var qtyRaw interface{}
		_ = json.Unmarshal(rawQty, &qtyRaw)
		switch v := qtyRaw.(type) {
		case float64:
			if v != float64(int(v)) {
				// float with fractional part
				validationErrors = append(validationErrors, validationDetail{
					Loc:  []interface{}{"body", "quantity"},
					Msg:  "Input should be a valid integer",
					Type: "int_parsing",
				})
			} else if int(v) <= 0 {
				validationErrors = append(validationErrors, validationDetail{
					Loc:  []interface{}{"body", "quantity"},
					Msg:  "Input should be greater than 0",
					Type: "greater_than",
				})
			} else {
				quantity = int(v)
			}
		default:
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "quantity"},
				Msg:  "Input should be a valid integer",
				Type: "int_parsing",
			})
		}
	}

	// ---- price -------------------------------------------------------------
	var priceStr string
	if rawPrice, ok := raw["price"]; !ok {
		validationErrors = append(validationErrors, validationDetail{
			Loc:  []interface{}{"body", "price"},
			Msg:  "Field required",
			Type: "missing",
		})
	} else {
		// Accept a JSON string like "9.99" or a JSON number like 9.99
		var priceRaw interface{}
		_ = json.Unmarshal(rawPrice, &priceRaw)
		switch v := priceRaw.(type) {
		case string:
			f, err := strconv.ParseFloat(v, 64)
			if err != nil || f < 0.01 {
				validationErrors = append(validationErrors, validationDetail{
					Loc:  []interface{}{"body", "price"},
					Msg:  "Input should be greater than or equal to 0.01",
					Type: "decimal_parsing",
				})
			} else {
				priceStr = v
			}
		case float64:
			if v < 0.01 {
				validationErrors = append(validationErrors, validationDetail{
					Loc:  []interface{}{"body", "price"},
					Msg:  "Input should be greater than or equal to 0.01",
					Type: "greater_than_equal",
				})
			} else {
				priceStr = strconv.FormatFloat(v, 'f', -1, 64)
			}
		default:
			validationErrors = append(validationErrors, validationDetail{
				Loc:  []interface{}{"body", "price"},
				Msg:  "Input should be a valid decimal number",
				Type: "decimal_parsing",
			})
		}
	}

	if len(validationErrors) > 0 {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]interface{}{
			"detail": validationErrors,
		})
		return
	}

	order := h.Repo.CreateOrder(productID, quantity, priceStr)

	writeJSON(w, http.StatusCreated, orderResponse{
		OrderID:   order.OrderID,
		ProductID: order.ProductID,
		Quantity:  order.Quantity,
		Price:     order.Price,
		Status:    order.Status,
		CreatedAt: order.CreatedAt.Format("2006-01-02T15:04:05.999999999Z07:00"),
	})
}
