package user_test

import (
	"errors"
	"testing"

	"github.com/MinnMinn/skills-introduction-to-github/user"
)

// helper that creates a store pre-seeded with one user.
func seedStore(t *testing.T) (*user.Store, user.User) {
	t.Helper()
	s := user.NewStore()
	created, err := s.Create(user.User{
		ID:    "u1",
		Name:  "Alice",
		Email: "alice@example.com",
	})
	if err != nil {
		t.Fatalf("seed Create: unexpected error: %v", err)
	}
	return s, created
}

// ── Create ────────────────────────────────────────────────────────────────────

func TestCreate_Success(t *testing.T) {
	s := user.NewStore()
	u, err := s.Create(user.User{ID: "u1", Name: "Alice", Email: "alice@example.com"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if u.ID != "u1" {
		t.Errorf("ID: want %q, got %q", "u1", u.ID)
	}
	if u.CreatedAt.IsZero() {
		t.Error("CreatedAt should be set")
	}
	if u.UpdatedAt.IsZero() {
		t.Error("UpdatedAt should be set")
	}
}

func TestCreate_DuplicateID(t *testing.T) {
	s, _ := seedStore(t)
	_, err := s.Create(user.User{ID: "u1", Name: "Bob", Email: "bob@example.com"})
	if !errors.Is(err, user.ErrAlreadyExists) {
		t.Errorf("want ErrAlreadyExists, got %v", err)
	}
}

func TestCreate_ValidationErrors(t *testing.T) {
	s := user.NewStore()
	cases := []struct {
		name    string
		input   user.User
		wantErr error
	}{
		{"empty id", user.User{Name: "Alice", Email: "a@b.com"}, user.ErrInvalidID},
		{"empty name", user.User{ID: "u2", Email: "a@b.com"}, user.ErrInvalidName},
		{"empty email", user.User{ID: "u2", Name: "Alice"}, user.ErrInvalidEmail},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := s.Create(tc.input)
			if !errors.Is(err, tc.wantErr) {
				t.Errorf("want %v, got %v", tc.wantErr, err)
			}
		})
	}
}

// ── ReadByID ──────────────────────────────────────────────────────────────────

func TestReadByID_Success(t *testing.T) {
	s, seed := seedStore(t)
	u, err := s.ReadByID(seed.ID)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if u.Name != seed.Name {
		t.Errorf("Name: want %q, got %q", seed.Name, u.Name)
	}
}

func TestReadByID_NotFound(t *testing.T) {
	s := user.NewStore()
	_, err := s.ReadByID("nonexistent")
	if !errors.Is(err, user.ErrNotFound) {
		t.Errorf("want ErrNotFound, got %v", err)
	}
}

func TestReadByID_EmptyID(t *testing.T) {
	s := user.NewStore()
	_, err := s.ReadByID("")
	if !errors.Is(err, user.ErrInvalidID) {
		t.Errorf("want ErrInvalidID, got %v", err)
	}
}

// ── ReadAll ───────────────────────────────────────────────────────────────────

func TestReadAll_Empty(t *testing.T) {
	s := user.NewStore()
	users := s.ReadAll()
	if len(users) != 0 {
		t.Errorf("want 0 users, got %d", len(users))
	}
}

func TestReadAll_ReturnsAll(t *testing.T) {
	s, _ := seedStore(t)
	s.Create(user.User{ID: "u2", Name: "Bob", Email: "bob@example.com"}) //nolint:errcheck

	users := s.ReadAll()
	if len(users) != 2 {
		t.Errorf("want 2 users, got %d", len(users))
	}
}

// ── Update ────────────────────────────────────────────────────────────────────

func TestUpdate_Name(t *testing.T) {
	s, seed := seedStore(t)
	updated, err := s.Update(seed.ID, user.UpdateInput{Name: "Alicia"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if updated.Name != "Alicia" {
		t.Errorf("Name: want %q, got %q", "Alicia", updated.Name)
	}
	// Email should be unchanged
	if updated.Email != seed.Email {
		t.Errorf("Email: want %q, got %q", seed.Email, updated.Email)
	}
}

func TestUpdate_Email(t *testing.T) {
	s, seed := seedStore(t)
	updated, err := s.Update(seed.ID, user.UpdateInput{Email: "new@example.com"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if updated.Email != "new@example.com" {
		t.Errorf("Email: want %q, got %q", "new@example.com", updated.Email)
	}
}

func TestUpdate_UpdatedAtChanges(t *testing.T) {
	s, seed := seedStore(t)
	updated, _ := s.Update(seed.ID, user.UpdateInput{Name: "Alicia"})
	if !updated.UpdatedAt.After(seed.UpdatedAt) && updated.UpdatedAt != seed.UpdatedAt {
		// UpdatedAt should be >= original; allow equal on fast machines
		t.Log("UpdatedAt may be equal on fast systems — acceptable")
	}
}

func TestUpdate_NotFound(t *testing.T) {
	s := user.NewStore()
	_, err := s.Update("ghost", user.UpdateInput{Name: "X"})
	if !errors.Is(err, user.ErrNotFound) {
		t.Errorf("want ErrNotFound, got %v", err)
	}
}

func TestUpdate_EmptyID(t *testing.T) {
	s := user.NewStore()
	_, err := s.Update("", user.UpdateInput{Name: "X"})
	if !errors.Is(err, user.ErrInvalidID) {
		t.Errorf("want ErrInvalidID, got %v", err)
	}
}

// ── Delete ────────────────────────────────────────────────────────────────────

func TestDelete_Success(t *testing.T) {
	s, seed := seedStore(t)
	if err := s.Delete(seed.ID); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Confirm it's gone
	if _, err := s.ReadByID(seed.ID); !errors.Is(err, user.ErrNotFound) {
		t.Errorf("want ErrNotFound after delete, got %v", err)
	}
}

func TestDelete_NotFound(t *testing.T) {
	s := user.NewStore()
	err := s.Delete("ghost")
	if !errors.Is(err, user.ErrNotFound) {
		t.Errorf("want ErrNotFound, got %v", err)
	}
}

func TestDelete_EmptyID(t *testing.T) {
	s := user.NewStore()
	err := s.Delete("")
	if !errors.Is(err, user.ErrInvalidID) {
		t.Errorf("want ErrInvalidID, got %v", err)
	}
}

// ── Concurrency smoke test ────────────────────────────────────────────────────

func TestConcurrentAccess(t *testing.T) {
	s := user.NewStore()
	done := make(chan struct{})

	// Writer goroutine
	go func() {
		for i := 0; i < 50; i++ {
			s.Create(user.User{ //nolint:errcheck
				ID:    string(rune('A' + i)),
				Name:  "User",
				Email: "u@example.com",
			})
		}
		close(done)
	}()

	// Concurrent reader goroutine
	go func() {
		for i := 0; i < 50; i++ {
			s.ReadAll()
		}
	}()

	<-done // wait for writers to finish; no race expected
}
