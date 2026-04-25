// Package models contains the domain structs that mirror the database tables.
//
// Tables:
//
//	user_settings — per-user application preferences
//	orders        — customer orders
package models

import "time"

// UserSettings mirrors a row in the `user_settings` table.
//
// Columns:
//
//	user_id       TEXT PRIMARY KEY
//	theme         TEXT    ("light" | "dark")
//	language      TEXT    (e.g. "en", "fr")
//	notifications BOOLEAN
//	timezone      TEXT    (e.g. "UTC", "America/New_York")
//	updated_at    TEXT    (ISO-8601 timestamp)
type UserSettings struct {
	UserID        string `json:"user_id"`
	Theme         string `json:"theme"`
	Language      string `json:"language"`
	Notifications bool   `json:"notifications"`
	Timezone      string `json:"timezone"`
	UpdatedAt     string `json:"updated_at"`
}

// NewUserSettings creates a UserSettings with sensible defaults.
func NewUserSettings(userID string) *UserSettings {
	return &UserSettings{
		UserID:        userID,
		Theme:         "light",
		Language:      "en",
		Notifications: true,
		Timezone:      "UTC",
		UpdatedAt:     time.Now().UTC().Format(time.RFC3339Nano),
	}
}

// Order mirrors a row in the `orders` table.
//
// Columns:
//
//	order_id   TEXT PRIMARY KEY  (UUID string)
//	product_id TEXT              (UUID string)
//	quantity   INTEGER
//	price      TEXT              (decimal string)
//	status     TEXT              ("pending")
//	created_at TEXT              (ISO-8601 timestamp)
type Order struct {
	OrderID   string `json:"order_id"`
	ProductID string `json:"product_id"`
	Quantity  int    `json:"quantity"`
	Price     string `json:"price"`
	Status    string `json:"status"`
	CreatedAt string `json:"created_at"`
}
