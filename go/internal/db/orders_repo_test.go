package db

import (
	"regexp"
	"testing"

	"github.com/MinnMinn/skills-introduction-to-github/internal/models"
)

var uuidPattern = regexp.MustCompile(
	`(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`,
)

// ---------------------------------------------------------------------------
// OrdersRepository unit tests
// ---------------------------------------------------------------------------

func TestOrdersRepository_CreateOrderReturnsRecord(t *testing.T) {
	repo := NewOrdersRepository()

	order, err := repo.CreateOrder("prod-uuid-1234", 3, "9.99")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if order == nil {
		t.Fatal("expected order, got nil")
	}
	if order.ProductID != "prod-uuid-1234" {
		t.Errorf("ProductID mismatch: got %q", order.ProductID)
	}
	if order.Quantity != 3 {
		t.Errorf("Quantity mismatch: got %d", order.Quantity)
	}
	if order.Price != "9.99" {
		t.Errorf("Price mismatch: got %q", order.Price)
	}
	if order.Status != "pending" {
		t.Errorf("Status mismatch: got %q", order.Status)
	}
}

func TestOrdersRepository_CreateOrderGeneratesUUIDOrderID(t *testing.T) {
	repo := NewOrdersRepository()

	order, _ := repo.CreateOrder("prod-uuid-1234", 1, "1.00")
	if !uuidPattern.MatchString(order.OrderID) {
		t.Errorf("order_id is not a valid UUID: %q", order.OrderID)
	}
}

func TestOrdersRepository_CreateOrderOrderIDIsUnique(t *testing.T) {
	repo := NewOrdersRepository()

	o1, _ := repo.CreateOrder("prod-1", 1, "1.00")
	o2, _ := repo.CreateOrder("prod-2", 2, "2.00")

	if o1.OrderID == o2.OrderID {
		t.Errorf("expected unique order IDs, both got %q", o1.OrderID)
	}
}

func TestOrdersRepository_GetReturnsSeededRecord(t *testing.T) {
	repo := NewOrdersRepository()
	order := &models.Order{
		OrderID:   "fixed-order-id",
		ProductID: "prod-1",
		Quantity:  5,
		Price:     "5.00",
		Status:    "pending",
	}
	repo.Seed(order)

	got := repo.Get("fixed-order-id")
	if got == nil {
		t.Fatal("expected record, got nil")
	}
	if got.Quantity != 5 {
		t.Errorf("expected quantity 5, got %d", got.Quantity)
	}
}

func TestOrdersRepository_GetReturnsNilForMissing(t *testing.T) {
	repo := NewOrdersRepository()
	if got := repo.Get("no-such-order"); got != nil {
		t.Errorf("expected nil, got %v", got)
	}
}

func TestOrdersRepository_ClearEmptiesStore(t *testing.T) {
	repo := NewOrdersRepository()
	order := &models.Order{OrderID: "o1", ProductID: "p1", Quantity: 1, Price: "1.00", Status: "pending"}
	repo.Seed(order)
	repo.Clear()

	if got := repo.Get("o1"); got != nil {
		t.Errorf("expected nil after Clear(), got %v", got)
	}
}
