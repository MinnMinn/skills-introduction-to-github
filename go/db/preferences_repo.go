// Package db contains the repository layer for all data-access operations.
// Each repository uses an in-memory store so it can be swapped for a real
// database connection without touching the API layer.
package db

import (
	"fmt"
	"sync"
	"time"

	"github.com/MinnMinn/skills-introduction-to-github/models"
)

// PreferencesRepository provides CRUD operations against the `user_settings`
// table. The in-memory store is protected by a read/write mutex so the
// repository is safe for concurrent use.
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

// Get returns the UserSettings for userID, or nil if not found.
func (r *PreferencesRepository) Get(userID string) *models.UserSettings {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.store[userID]
}

// Update applies a partial update to the preferences of userID.
// Only the non-zero fields inside fields are applied.
// Returns the updated record, or nil if the user does not exist.
// Returns an error when fields is empty.
func (r *PreferencesRepository) Update(userID string, fields PreferencesFields) (*models.UserSettings, error) {
	if fields.isEmpty() {
		return nil, fmt.Errorf("no fields supplied for update")
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	record, ok := r.store[userID]
	if !ok {
		return nil, nil //nolint:nilnil // nil,nil signals "not found" to the caller
	}

	if fields.Theme != nil {
		record.Theme = *fields.Theme
	}
	if fields.Language != nil {
		record.Language = *fields.Language
	}
	if fields.Notifications != nil {
		record.Notifications = *fields.Notifications
	}
	if fields.Timezone != nil {
		record.Timezone = *fields.Timezone
	}
	record.UpdatedAt = time.Now().UTC().Format(time.RFC3339Nano)

	return record, nil
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

// PreferencesFields holds the optional fields accepted by Update.
// A nil pointer means "not supplied / leave unchanged".
type PreferencesFields struct {
	Theme         *string
	Language      *string
	Notifications *bool
	Timezone      *string
}

func (f PreferencesFields) isEmpty() bool {
	return f.Theme == nil && f.Language == nil &&
		f.Notifications == nil && f.Timezone == nil
}
