// Package db contains the repository layer for all database tables.
//
// PreferencesRepository isolates all data-access logic for `user_settings` so
// the API layer stays thin. Uses an in-memory store by default; swap _store
// for a real DB session in production without changing any API code.
package db

import (
	"fmt"
	"sync"
	"time"

	"github.com/MinnMinn/skills-introduction-to-github/internal/models"
)

// PreferencesRepository performs CRUD operations against `user_settings`.
type PreferencesRepository struct {
	mu     sync.RWMutex
	store  map[string]*models.UserSettings
}

// NewPreferencesRepository returns an initialised, empty repository.
func NewPreferencesRepository() *PreferencesRepository {
	return &PreferencesRepository{
		store: make(map[string]*models.UserSettings),
	}
}

// Get returns the UserSettings for userID, or nil if not found.
func (r *PreferencesRepository) Get(userID string) *models.UserSettings {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.store[userID]
}

// Update applies a partial update to the preferences of userID.
//
// Returns the updated *UserSettings, or nil if the user does not exist.
// Returns an error when fields is empty.
func (r *PreferencesRepository) Update(userID string, fields map[string]interface{}) (*models.UserSettings, error) {
	if len(fields) == 0 {
		return nil, fmt.Errorf("No fields supplied for update")
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	record, ok := r.store[userID]
	if !ok {
		return nil, nil //nolint:nilnil // nil,nil signals "not found" (caller checks)
	}

	for key, value := range fields {
		switch key {
		case "theme":
			if v, ok := value.(string); ok {
				record.Theme = v
			}
		case "language":
			if v, ok := value.(string); ok {
				record.Language = v
			}
		case "notifications":
			if v, ok := value.(bool); ok {
				record.Notifications = v
			}
		case "timezone":
			if v, ok := value.(string); ok {
				record.Timezone = v
			}
		}
	}

	record.UpdatedAt = time.Now().UTC().Format(time.RFC3339Nano)
	return record, nil
}

// ---------------------------------------------------------------------------
// Test / seed helpers (not part of the production interface)
// ---------------------------------------------------------------------------

// Seed inserts or overwrites a record — used by tests only.
func (r *PreferencesRepository) Seed(s *models.UserSettings) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.store[s.UserID] = s
}

// Clear removes all records — used by tests only.
func (r *PreferencesRepository) Clear() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.store = make(map[string]*models.UserSettings)
}
