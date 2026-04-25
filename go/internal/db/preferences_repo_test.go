package db

import (
	"testing"

	"github.com/MinnMinn/skills-introduction-to-github/internal/models"
)

// ---------------------------------------------------------------------------
// PreferencesRepository unit tests
// ---------------------------------------------------------------------------

func TestPreferencesRepository_GetReturnsNilForMissingUser(t *testing.T) {
	repo := NewPreferencesRepository()
	if got := repo.Get("nonexistent"); got != nil {
		t.Errorf("expected nil, got %v", got)
	}
}

func TestPreferencesRepository_GetReturnsSeededRecord(t *testing.T) {
	repo := NewPreferencesRepository()
	s := &models.UserSettings{UserID: "u1", Theme: "dark"}
	repo.Seed(s)

	got := repo.Get("u1")
	if got == nil {
		t.Fatal("expected record, got nil")
	}
	if got.Theme != "dark" {
		t.Errorf("expected theme 'dark', got %q", got.Theme)
	}
}

func TestPreferencesRepository_UpdateReturnsNilForMissingUser(t *testing.T) {
	repo := NewPreferencesRepository()
	result, err := repo.Update("nonexistent", map[string]interface{}{"theme": "dark"})
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if result != nil {
		t.Errorf("expected nil result for missing user, got %v", result)
	}
}

func TestPreferencesRepository_UpdateAppliesPartialFields(t *testing.T) {
	repo := NewPreferencesRepository()
	repo.Seed(&models.UserSettings{UserID: "u2", Theme: "light", Language: "en"})

	result, err := repo.Update("u2", map[string]interface{}{"theme": "dark"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result == nil {
		t.Fatal("expected updated record, got nil")
	}
	if result.Theme != "dark" {
		t.Errorf("expected theme 'dark', got %q", result.Theme)
	}
	if result.Language != "en" {
		t.Errorf("expected language 'en' (unchanged), got %q", result.Language)
	}
}

func TestPreferencesRepository_UpdateRaisesOnEmptyFields(t *testing.T) {
	repo := NewPreferencesRepository()
	repo.Seed(&models.UserSettings{UserID: "u3"})

	_, err := repo.Update("u3", map[string]interface{}{})
	if err == nil {
		t.Error("expected an error for empty fields map, got nil")
	}
}

func TestPreferencesRepository_ClearEmptiesStore(t *testing.T) {
	repo := NewPreferencesRepository()
	repo.Seed(&models.UserSettings{UserID: "u4"})
	repo.Clear()

	if got := repo.Get("u4"); got != nil {
		t.Errorf("expected nil after Clear(), got %v", got)
	}
}
