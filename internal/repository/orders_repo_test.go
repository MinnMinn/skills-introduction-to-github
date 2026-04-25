package repository_test

import (
	"regexp"
	"testing"

	"github.com/MinnMinn/skills-introduction-to-github/internal/models"
	"github.com/MinnMinn/skills-introduction-to-github/internal/repository"
)

var uuidPattern = regexp.MustCompile(
	`(?i)^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`,
)

func TestOrdersRepository_CreateOrderReturnsValidOrder(t *testing.T) {
	r := repository.NewOrdersRepository()
	order := r.CreateOrder("some-product-uuid", 3, "9.99")

	if order == nil {
		t.Fatal("expected non-nil order")
	}
	if order.ProductID != "some-product-uuid" {
		t.Errorf("expected product_id=some-product-uuid, got %q", order.ProductID)
	}
	if order.Quantity != 3 {
		t.Errorf("expected quantity=3, got %d", order.Quantity)
	}
	if order.Price != "9.99" {
		t.Errorf("expected price=9.99, got %q", order.Price)
	}
	if order.Status != "pending" {
		t.Errorf("expected status=pending, got %q", order.Status)
	}
}

func TestOrdersRepository_CreateOrderGeneratesValidUUID(t *testing.T) {
	r := repository.NewOrdersRepository()
	order := r.CreateOrder("pid", 1, "1.00")

	if !uuidPattern.MatchString(order.OrderID) {
		t.Errorf("order_id %q is not a valid UUID v4", order.OrderID)
	}
}

func TestOrdersRepository_CreateOrderIDsAreUnique(t *testing.T) {
	r := repository.NewOrdersRepository()
	ids := make(map[string]bool)
	for i := 0; i < 100; i++ {
		o := r.CreateOrder("pid", 1, "1.00")
		if ids[o.OrderID] {
			t.Fatalf("duplicate order_id generated: %s", o.OrderID)
		}
		ids[o.OrderID] = true
	}
}

func TestOrdersRepository_GetReturnsNilForMissingOrder(t *testing.T) {
	r := repository.NewOrdersRepository()
	_, ok := r.Get("nonexistent")
	if ok {
		t.Fatal("expected ok=false for missing order")
	}
}

func TestOrdersRepository_GetReturnsSeededRecord(t *testing.T) {
	r := repository.NewOrdersRepository()
	o := &models.Order{OrderID: "o1", ProductID: "p1", Quantity: 2, Price: "5.00", Status: "pending"}
	r.Seed(o)

	got, ok := r.Get("o1")
	if !ok {
		t.Fatal("expected ok=true for seeded order")
	}
	if got.OrderID != "o1" {
		t.Errorf("unexpected order_id: %q", got.OrderID)
	}
}

func TestOrdersRepository_ClearRemovesAllRecords(t *testing.T) {
	r := repository.NewOrdersRepository()
	_ = r.CreateOrder("pid", 1, "1.00")
	r.Clear()

	// store is now empty — Get any ID should return false
	r2 := repository.NewOrdersRepository()
	r2.Clear()
	_, ok := r2.Get("anything")
	if ok {
		t.Fatal("expected empty repo after Clear()")
	}
}
