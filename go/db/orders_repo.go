package db

import (
	"crypto/rand"
	"fmt"
	"sync"
	"time"

	"github.com/MinnMinn/skills-introduction-to-github/models"
)

// OrdersRepository provides CRUD operations against the `orders` table.
// The in-memory store is protected by a read/write mutex.
type OrdersRepository struct {
	mu    sync.RWMutex
	store map[string]*models.Order
}

// NewOrdersRepository returns an initialised, empty repository.
func NewOrdersRepository() *OrdersRepository {
	return &OrdersRepository{
		store: make(map[string]*models.Order),
	}
}

// Get returns the Order for orderID, or nil if not found.
func (r *OrdersRepository) Get(orderID string) *models.Order {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.store[orderID]
}

// CreateOrder persists a new order and returns the created record.
// productID must be a valid UUID string; quantity must be > 0; price must be
// a decimal string ≥ "0.01" (caller is responsible for validation).
func (r *OrdersRepository) CreateOrder(productID string, quantity int, price string) (*models.Order, error) {
	orderID, err := newUUID()
	if err != nil {
		return nil, fmt.Errorf("generating order id: %w", err)
	}

	order := &models.Order{
		OrderID:   orderID,
		ProductID: productID,
		Quantity:  quantity,
		Price:     price,
		Status:    "pending",
		CreatedAt: time.Now().UTC().Format(time.RFC3339Nano),
	}

	r.mu.Lock()
	r.store[orderID] = order
	r.mu.Unlock()

	return order, nil
}

// Seed inserts or overwrites a record — used by tests only.
func (r *OrdersRepository) Seed(o *models.Order) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.store[o.OrderID] = o
}

// Clear removes all records — used by tests only.
func (r *OrdersRepository) Clear() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.store = make(map[string]*models.Order)
}

// newUUID generates a random UUID v4 string using crypto/rand.
func newUUID() (string, error) {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	// Set version 4 and variant bits.
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf(
		"%08x-%04x-%04x-%04x-%012x",
		b[0:4], b[4:6], b[6:8], b[8:10], b[10:],
	), nil
}
