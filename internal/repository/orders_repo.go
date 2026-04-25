package repository

import (
	"sync"
	"time"

	"github.com/MinnMinn/skills-introduction-to-github/internal/models"
	"github.com/google/uuid"
)

// OrdersRepository manages Order records.
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

// Get returns the Order for orderID, or (nil, false) if not found.
func (r *OrdersRepository) Get(orderID string) (*models.Order, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	o, ok := r.store[orderID]
	return o, ok
}

// CreateOrder persists a new order and returns the created record.
//
// Parameters
//   - productID : UUID string identifying the product (caller must validate)
//   - quantity  : number of units ordered (caller must ensure > 0)
//   - price     : unit price as a decimal string (caller must ensure >= 0.01)
func (r *OrdersRepository) CreateOrder(productID string, quantity int, price string) *models.Order {
	order := &models.Order{
		OrderID:   uuid.NewString(),
		ProductID: productID,
		Quantity:  quantity,
		Price:     price,
		Status:    "pending",
		CreatedAt: time.Now().UTC(),
	}

	r.mu.Lock()
	r.store[order.OrderID] = order
	r.mu.Unlock()

	return order
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
