package db_test

import (
	"testing"

	"github.com/MinnMinn/skills-introduction-to-github/db"
	"github.com/MinnMinn/skills-introduction-to-github/models"
)

// ---------------------------------------------------------------------------
// Get
// ---------------------------------------------------------------------------

func TestOrdersRepo_Get_ReturnsNilForMissing(t *testing.T) {
	r := db.NewOrdersRepository()
	if got := r.Get("no-such-id"); got != nil {
		t.Fatalf("expected nil, got %+v", got)
	}
}

func TestOrdersRepo_Get_ReturnsSeededRecord(t *testing.T) {
	r := db.NewOrdersRepository()
	o := &models.Order{OrderID: "oid-1", ProductID: "pid-1", Quantity: 1, Price: "1.00", Status: "pending"}
	r.Seed(o)

	got := r.Get("oid-1")
	if got != o {
		t.Fatalf("expected seeded record, got %+v", got)
	}
}

// ---------------------------------------------------------------------------
// CreateOrder
// ---------------------------------------------------------------------------

func TestOrdersRepo_CreateOrder_ReturnsOrderWithUUID(t *testing.T) {
	r := db.NewOrdersRepository()
	order, err := r.CreateOrder("550e8400-e29b-41d4-a716-446655440000", 3, "9.99")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if order.OrderID == "" {
		t.Error("order_id should not be empty")
	}
}

func TestOrdersRepo_CreateOrder_ReflectsSuppliedValues(t *testing.T) {
	r := db.NewOrdersRepository()
	pid := "550e8400-e29b-41d4-a716-446655440000"
	order, _ := r.CreateOrder(pid, 5, "19.99")

	if order.ProductID != pid {
		t.Errorf("expected product_id=%s, got %s", pid, order.ProductID)
	}
	if order.Quantity != 5 {
		t.Errorf("expected quantity=5, got %d", order.Quantity)
	}
	if order.Price != "19.99" {
		t.Errorf("expected price=19.99, got %s", order.Price)
	}
}

func TestOrdersRepo_CreateOrder_StatusIsPending(t *testing.T) {
	r := db.NewOrdersRepository()
	order, _ := r.CreateOrder("550e8400-e29b-41d4-a716-446655440000", 1, "0.01")
	if order.Status != "pending" {
		t.Errorf("expected status=pending, got %s", order.Status)
	}
}

func TestOrdersRepo_CreateOrder_CreatedAtIsNonEmpty(t *testing.T) {
	r := db.NewOrdersRepository()
	order, _ := r.CreateOrder("550e8400-e29b-41d4-a716-446655440000", 1, "1.00")
	if order.CreatedAt == "" {
		t.Error("created_at should not be empty")
	}
}

func TestOrdersRepo_CreateOrder_CanBeRetrievedByGet(t *testing.T) {
	r := db.NewOrdersRepository()
	order, _ := r.CreateOrder("550e8400-e29b-41d4-a716-446655440000", 2, "5.00")
	got := r.Get(order.OrderID)
	if got != order {
		t.Error("created order should be retrievable via Get")
	}
}

// ---------------------------------------------------------------------------
// Clear
// ---------------------------------------------------------------------------

func TestOrdersRepo_Clear_RemovesAllRecords(t *testing.T) {
	r := db.NewOrdersRepository()
	order, _ := r.CreateOrder("550e8400-e29b-41d4-a716-446655440000", 1, "1.00")
	r.Clear()
	if got := r.Get(order.OrderID); got != nil {
		t.Fatalf("expected nil after Clear, got %+v", got)
	}
}
