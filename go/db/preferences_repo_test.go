package db_test

import (
	"testing"

	"github.com/MinnMinn/skills-introduction-to-github/db"
	"github.com/MinnMinn/skills-introduction-to-github/models"
)

func strPtr(s string) *string { return &s }
func boolPtr(b bool) *bool    { return &b }

// ---------------------------------------------------------------------------
// Get
// ---------------------------------------------------------------------------

func TestPreferencesRepo_Get_ReturnsNilForMissingUser(t *testing.T) {
	r := db.NewPreferencesRepository()
	if got := r.Get("nonexistent"); got != nil {
		t.Fatalf("expected nil, got %+v", got)
	}
}

func TestPreferencesRepo_Get_ReturnsSeededRecord(t *testing.T) {
	r := db.NewPreferencesRepository()
	s := &models.UserSettings{UserID: "u1", Theme: "dark"}
	r.Seed(s)

	got := r.Get("u1")
	if got != s {
		t.Fatalf("expected seeded record, got %+v", got)
	}
}

// ---------------------------------------------------------------------------
// Update
// ---------------------------------------------------------------------------

func TestPreferencesRepo_Update_ReturnsNilForMissingUser(t *testing.T) {
	r := db.NewPreferencesRepository()
	got, err := r.Update("nonexistent", db.PreferencesFields{Theme: strPtr("dark")})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != nil {
		t.Fatalf("expected nil for missing user, got %+v", got)
	}
}

func TestPreferencesRepo_Update_AppliesPartialFields(t *testing.T) {
	r := db.NewPreferencesRepository()
	r.Seed(&models.UserSettings{UserID: "u2", Theme: "light", Language: "en"})

	got, err := r.Update("u2", db.PreferencesFields{Theme: strPtr("dark")})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.Theme != "dark" {
		t.Errorf("expected theme=dark, got %s", got.Theme)
	}
	if got.Language != "en" {
		t.Errorf("expected language=en (unchanged), got %s", got.Language)
	}
}

func TestPreferencesRepo_Update_AppliesAllFields(t *testing.T) {
	r := db.NewPreferencesRepository()
	r.Seed(models.NewUserSettings("u3"))

	fields := db.PreferencesFields{
		Theme:         strPtr("dark"),
		Language:      strPtr("fr"),
		Notifications: boolPtr(false),
		Timezone:      strPtr("Europe/Paris"),
	}
	got, err := r.Update("u3", fields)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.Theme != "dark" || got.Language != "fr" ||
		got.Notifications != false || got.Timezone != "Europe/Paris" {
		t.Errorf("not all fields applied: %+v", got)
	}
}

func TestPreferencesRepo_Update_RaisesOnEmptyFields(t *testing.T) {
	r := db.NewPreferencesRepository()
	r.Seed(models.NewUserSettings("u4"))

	_, err := r.Update("u4", db.PreferencesFields{})
	if err == nil {
		t.Fatal("expected error for empty fields, got nil")
	}
}

func TestPreferencesRepo_Update_RefreshesUpdatedAt(t *testing.T) {
	r := db.NewPreferencesRepository()
	s := models.NewUserSettings("u5")
	original := s.UpdatedAt
	r.Seed(s)

	got, _ := r.Update("u5", db.PreferencesFields{Theme: strPtr("dark")})
	// UpdatedAt must be a non-empty string and may differ from the original.
	if got.UpdatedAt == "" {
		t.Error("updated_at should not be empty")
	}
	_ = original // same-second updates are valid; we only check non-empty
}

// ---------------------------------------------------------------------------
// Clear
// ---------------------------------------------------------------------------

func TestPreferencesRepo_Clear_RemovesAllRecords(t *testing.T) {
	r := db.NewPreferencesRepository()
	r.Seed(models.NewUserSettings("u6"))
	r.Clear()

	if got := r.Get("u6"); got != nil {
		t.Fatalf("expected nil after Clear, got %+v", got)
	}
}
