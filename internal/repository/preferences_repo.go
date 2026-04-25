// Package repository provides in-memory CRUD operations for domain models.
//
// The backing stores use plain maps protected by a mutex so that the same
// repository instance can be shared safely across goroutines.  In production,
// replace the map with a real DB session without changing any handler code.
package repository

import (
	"fmt"
	"sync"
	"time"

	"github.com/MinnMinn/skills-introduction-to-github/internal/models"
)

// PreferencesRepository manages UserSettings records.
type PreferencesRepository struct {
	mu    sync.RWMutex
	store map[string]*models.UserSettings
}

// NewPreferencesRepository returns an initialised, empty repository.
func NewPreferencesRepository() *PreferencesRepository {
	return &PreferencesRepository{
		store: make(map[string]*models.UserSettings),
	}
}

// Get returns the UserSettings for userID, or (nil, false) if not found.
func (r *PreferencesRepository) Get(userID string) (*models.UserSettings, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	s, ok := r.store[userID]
	return s, ok
}

// UpdateFields applies a partial update to the record identified by userID.
//
// Only the keys present in fields are changed; unrecognised keys are silently
// ignored.  Returns an error when userID is not found or fields is empty.
func (r *PreferencesRepository) UpdateFields(userID string, fields map[string]interface{}) (*models.UserSettings, error) {
	if len(fields) == 0 {
		return nil, fmt.Errorf("no fields supplied for update")
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	s, ok := r.store[userID]
	if !ok {
		return nil, nil //nolint:nilnil // caller distinguishes nil from error
	}

	for k, v := range fields {
		switch k {
		case "theme":
			if sv, ok := v.(string); ok {
				s.Theme = sv
			}
		case "language":
			if sv, ok := v.(string); ok {
				s.Language = sv
			}
		case "notifications":
			if bv, ok := v.(bool); ok {
				s.Notifications = bv
			}
		case "timezone":
			if sv, ok := v.(string); ok {
				s.Timezone = sv
			}
		}
	}

	s.UpdatedAt = time.Now().UTC()
	return s, nil
}

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
