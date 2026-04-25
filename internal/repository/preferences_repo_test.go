package repository_test

import (
	"testing"

	"github.com/MinnMinn/skills-introduction-to-github/internal/models"
	"github.com/MinnMinn/skills-introduction-to-github/internal/repository"
)

func TestPreferencesRepository_GetReturnsNilForMissingUser(t *testing.T) {
	r := repository.NewPreferencesRepository()
	_, ok := r.Get("nonexistent")
	if ok {
		t.Fatal("expected ok=false for missing user")
	}
}

func TestPreferencesRepository_GetReturnsSeededRecord(t *testing.T) {
	r := repository.NewPreferencesRepository()
	s := models.NewUserSettings("u1")
	s.Theme = "dark"
	r.Seed(s)

	got, ok := r.Get("u1")
	if !ok {
		t.Fatal("expected ok=true for seeded user")
	}
	if got.Theme != "dark" {
		t.Errorf("expected theme=dark, got %q", got.Theme)
	}
}

func TestPreferencesRepository_UpdateReturnsNilForMissingUser(t *testing.T) {
	r := repository.NewPreferencesRepository()
	r.Clear()

	s, err := r.UpdateFields("nonexistent", map[string]interface{}{"theme": "dark"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if s != nil {
		t.Fatal("expected nil result for missing user")
	}
}

func TestPreferencesRepository_UpdateAppliesPartialFields(t *testing.T) {
	r := repository.NewPreferencesRepository()
	s := models.NewUserSettings("u2")
	s.Theme = "light"
	s.Language = "en"
	r.Seed(s)

	result, err := r.UpdateFields("u2", map[string]interface{}{"theme": "dark"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result == nil {
		t.Fatal("expected non-nil result")
	}
	if result.Theme != "dark" {
		t.Errorf("expected theme=dark, got %q", result.Theme)
	}
	if result.Language != "en" {
		t.Errorf("expected language to be unchanged (en), got %q", result.Language)
	}
}

func TestPreferencesRepository_UpdateRaisesOnEmptyFields(t *testing.T) {
	r := repository.NewPreferencesRepository()
	r.Seed(models.NewUserSettings("u3"))

	_, err := r.UpdateFields("u3", map[string]interface{}{})
	if err == nil {
		t.Fatal("expected error for empty fields map")
	}
}

func TestPreferencesRepository_ClearRemovesAllRecords(t *testing.T) {
	r := repository.NewPreferencesRepository()
	r.Seed(models.NewUserSettings("u4"))
	r.Clear()

	_, ok := r.Get("u4")
	if ok {
		t.Fatal("expected record to be gone after Clear()")
	}
}

func TestPreferencesRepository_UpdateRefreshesUpdatedAt(t *testing.T) {
	r := repository.NewPreferencesRepository()
	s := models.NewUserSettings("u5")
	before := s.UpdatedAt
	r.Seed(s)

	result, _ := r.UpdateFields("u5", map[string]interface{}{"theme": "dark"})
	if result == nil {
		t.Fatal("expected non-nil result")
	}
	// UpdatedAt must be equal to or after the original timestamp
	if result.UpdatedAt.Before(before) {
		t.Error("UpdatedAt should not go backwards after update")
	}
}
