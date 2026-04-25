package handlers_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"regexp"
	"testing"

	"github.com/MinnMinn/skills-introduction-to-github/internal/handlers"
	"github.com/MinnMinn/skills-introduction-to-github/internal/repository"
)

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

var uuidRegexp = regexp.MustCompile(
	`(?i)^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`,
)

func newOrdersHandler() (*handlers.OrdersHandler, *repository.OrdersRepository) {
	repo := repository.NewOrdersRepository()
	return &handlers.OrdersHandler{Repo: repo}, repo
}

func doOrdersPOST(t *testing.T, h *handlers.OrdersHandler, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	mux := http.NewServeMux()
	mux.HandleFunc("POST /api/v1/orders", h.CreateOrder)
	var b []byte
	switch v := body.(type) {
	case string:
		b = []byte(v)
	default:
		b, _ = json.Marshal(v)
	}
	req := httptest.NewRequest(http.MethodPost, "/api/v1/orders", bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	return w
}

const validProductID = "550e8400-e29b-41d4-a716-446655440000"

var validPayload = map[string]interface{}{
	"product_id": validProductID,
	"quantity":   3,
	"price":      "9.99",
}

// ---------------------------------------------------------------------------
// POST — happy path
// ---------------------------------------------------------------------------

func TestCreateOrder_Returns201ForValidPayload(t *testing.T) {
	h, _ := newOrdersHandler()
	w := doOrdersPOST(t, h, validPayload)
	if w.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", w.Code, w.Body.String())
	}
}

func TestCreateOrder_ResponseContainsAllExpectedKeys(t *testing.T) {
	h, _ := newOrdersHandler()
	w := doOrdersPOST(t, h, validPayload)

	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)
	expected := []string{"order_id", "product_id", "quantity", "price", "status", "created_at"}
	for _, k := range expected {
		if _, ok := body[k]; !ok {
			t.Errorf("missing key: %s", k)
		}
	}
}

func TestCreateOrder_ResponseReflectsSubmittedValues(t *testing.T) {
	h, _ := newOrdersHandler()
	w := doOrdersPOST(t, h, validPayload)

	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)

	if body["product_id"] != validProductID {
		t.Errorf("unexpected product_id: %v", body["product_id"])
	}
	if body["quantity"].(float64) != 3 {
		t.Errorf("unexpected quantity: %v", body["quantity"])
	}
	if body["price"] != "9.99" {
		t.Errorf("unexpected price: %v", body["price"])
	}
}

func TestCreateOrder_ResponseOrderIDIsValidUUID(t *testing.T) {
	h, _ := newOrdersHandler()
	w := doOrdersPOST(t, h, validPayload)

	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)
	orderID, _ := body["order_id"].(string)
	if !uuidRegexp.MatchString(orderID) {
		t.Errorf("order_id %q is not a valid UUID", orderID)
	}
}

func TestCreateOrder_ResponseStatusIsPending(t *testing.T) {
	h, _ := newOrdersHandler()
	w := doOrdersPOST(t, h, validPayload)

	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)
	if body["status"] != "pending" {
		t.Errorf("expected status=pending, got %v", body["status"])
	}
}

func TestCreateOrder_MinimumValidQuantityAndPrice(t *testing.T) {
	h, _ := newOrdersHandler()
	payload := map[string]interface{}{"product_id": validProductID, "quantity": 1, "price": "0.01"}
	w := doOrdersPOST(t, h, payload)
	if w.Code != http.StatusCreated {
		t.Fatalf("expected 201 for minimum values, got %d: %s", w.Code, w.Body.String())
	}
}

func TestCreateOrder_LargeQuantityAndPrice(t *testing.T) {
	h, _ := newOrdersHandler()
	payload := map[string]interface{}{"product_id": validProductID, "quantity": 1000000, "price": "99999.99"}
	w := doOrdersPOST(t, h, payload)
	if w.Code != http.StatusCreated {
		t.Fatalf("expected 201 for large values, got %d: %s", w.Code, w.Body.String())
	}
}

// ---------------------------------------------------------------------------
// POST — missing required fields → 422
// ---------------------------------------------------------------------------

func TestCreateOrder_MissingProductIDReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	w := doOrdersPOST(t, h, map[string]interface{}{"quantity": 2, "price": "5.00"})
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestCreateOrder_MissingQuantityReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	w := doOrdersPOST(t, h, map[string]interface{}{"product_id": validProductID, "price": "5.00"})
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestCreateOrder_MissingPriceReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	w := doOrdersPOST(t, h, map[string]interface{}{"product_id": validProductID, "quantity": 2})
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestCreateOrder_EmptyBodyReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	w := doOrdersPOST(t, h, map[string]interface{}{})
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

// ---------------------------------------------------------------------------
// POST — invalid quantity → 422
// ---------------------------------------------------------------------------

func TestCreateOrder_QuantityZeroReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	payload := map[string]interface{}{"product_id": validProductID, "quantity": 0, "price": "9.99"}
	w := doOrdersPOST(t, h, payload)
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestCreateOrder_NegativeQuantityReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	payload := map[string]interface{}{"product_id": validProductID, "quantity": -1, "price": "9.99"}
	w := doOrdersPOST(t, h, payload)
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestCreateOrder_FloatQuantityReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	w := doOrdersPOST(t, h, `{"product_id":"`+validProductID+`","quantity":1.5,"price":"9.99"}`)
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d: %s", w.Code, w.Body.String())
	}
}

func TestCreateOrder_StringQuantityReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	w := doOrdersPOST(t, h, `{"product_id":"`+validProductID+`","quantity":"two","price":"9.99"}`)
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

// ---------------------------------------------------------------------------
// POST — invalid price → 422
// ---------------------------------------------------------------------------

func TestCreateOrder_PriceZeroReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	payload := map[string]interface{}{"product_id": validProductID, "quantity": 1, "price": "0.00"}
	w := doOrdersPOST(t, h, payload)
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestCreateOrder_NegativePriceReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	payload := map[string]interface{}{"product_id": validProductID, "quantity": 1, "price": "-1.00"}
	w := doOrdersPOST(t, h, payload)
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestCreateOrder_StringPriceReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	payload := map[string]interface{}{"product_id": validProductID, "quantity": 1, "price": "free"}
	w := doOrdersPOST(t, h, payload)
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

// ---------------------------------------------------------------------------
// POST — invalid product_id → 422
// ---------------------------------------------------------------------------

func TestCreateOrder_NonUUIDStringReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	payload := map[string]interface{}{"product_id": "not-a-uuid", "quantity": 1, "price": "9.99"}
	w := doOrdersPOST(t, h, payload)
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestCreateOrder_IntegerProductIDReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	payload := map[string]interface{}{"product_id": 12345, "quantity": 1, "price": "9.99"}
	w := doOrdersPOST(t, h, payload)
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

func TestCreateOrder_EmptyStringProductIDReturns422(t *testing.T) {
	h, _ := newOrdersHandler()
	payload := map[string]interface{}{"product_id": "", "quantity": 1, "price": "9.99"}
	w := doOrdersPOST(t, h, payload)
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
}

// ---------------------------------------------------------------------------
// POST — 422 response has detail key
// ---------------------------------------------------------------------------

func TestCreateOrder_422BodyContainsDetailKey(t *testing.T) {
	h, _ := newOrdersHandler()
	payload := map[string]interface{}{"product_id": validProductID, "quantity": -1, "price": "9.99"}
	w := doOrdersPOST(t, h, payload)

	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", w.Code)
	}
	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)
	if _, ok := body["detail"]; !ok {
		t.Error("expected 'detail' key in 422 response")
	}
}
