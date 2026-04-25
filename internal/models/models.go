// Package models contains the domain structs used throughout the application.
//
// These mirror the Python dataclasses in src/db/models.py.
package models

import "time"

// UserSettings represents a row in the user_settings table.
type UserSettings struct {
	UserID        string    `json:"user_id"`
	Theme         string    `json:"theme"`         // "light" | "dark"
	Language      string    `json:"language"`      // e.g. "en", "fr"
	Notifications bool      `json:"notifications"`
	Timezone      string    `json:"timezone"`      // e.g. "UTC", "America/New_York"
	UpdatedAt     time.Time `json:"updated_at"`
}

// NewUserSettings creates a UserSettings with sensible defaults.
func NewUserSettings(userID string) *UserSettings {
	return &UserSettings{
		UserID:        userID,
		Theme:         "light",
		Language:      "en",
		Notifications: true,
		Timezone:      "UTC",
		UpdatedAt:     time.Now().UTC(),
	}
}

// Order represents a row in the orders table.
type Order struct {
	OrderID   string    `json:"order_id"`
	ProductID string    `json:"product_id"`
	Quantity  int       `json:"quantity"`
	Price     string    `json:"price"`      // decimal string to avoid float precision loss
	Status    string    `json:"status"`     // e.g. "pending"
	CreatedAt time.Time `json:"created_at"`
}
