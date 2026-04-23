// Package user provides a simple in-memory store for User entities
// with full Create, Read, Update, and Delete (CRUD) operations.
package user

import (
	"errors"
	"sync"
	"time"
)

// Common sentinel errors returned by Store methods.
var (
	ErrNotFound      = errors.New("user: not found")
	ErrAlreadyExists = errors.New("user: id already exists")
	ErrInvalidID     = errors.New("user: id must not be empty")
	ErrInvalidName   = errors.New("user: name must not be empty")
	ErrInvalidEmail  = errors.New("user: email must not be empty")
)

// User represents an application user.
type User struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Email     string    `json:"email"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// UpdateInput holds the fields that may be changed via Update.
// Only non-empty values are applied.
type UpdateInput struct {
	Name  string
	Email string
}

// Store is a thread-safe, in-memory repository of User records.
type Store struct {
	mu    sync.RWMutex
	users map[string]User
}

// NewStore creates and returns an empty Store.
func NewStore() *Store {
	return &Store{
		users: make(map[string]User),
	}
}

// Create adds a new User to the store.
// Returns ErrInvalidID, ErrInvalidName, or ErrInvalidEmail on bad input,
// and ErrAlreadyExists if the ID is already taken.
func (s *Store) Create(u User) (User, error) {
	if u.ID == "" {
		return User{}, ErrInvalidID
	}
	if u.Name == "" {
		return User{}, ErrInvalidName
	}
	if u.Email == "" {
		return User{}, ErrInvalidEmail
	}

	now := time.Now().UTC()
	u.CreatedAt = now
	u.UpdatedAt = now

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.users[u.ID]; exists {
		return User{}, ErrAlreadyExists
	}

	s.users[u.ID] = u
	return u, nil
}

// ReadByID retrieves a single User by its ID.
// Returns ErrNotFound when no match exists.
func (s *Store) ReadByID(id string) (User, error) {
	if id == "" {
		return User{}, ErrInvalidID
	}

	s.mu.RLock()
	defer s.mu.RUnlock()

	u, ok := s.users[id]
	if !ok {
		return User{}, ErrNotFound
	}
	return u, nil
}

// ReadAll returns a slice of all Users currently in the store.
// The order of results is not guaranteed.
func (s *Store) ReadAll() []User {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]User, 0, len(s.users))
	for _, u := range s.users {
		result = append(result, u)
	}
	return result
}

// Update applies the non-empty fields in inp to the User identified by id.
// Returns ErrInvalidID on empty id, or ErrNotFound when no match exists.
func (s *Store) Update(id string, inp UpdateInput) (User, error) {
	if id == "" {
		return User{}, ErrInvalidID
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	u, ok := s.users[id]
	if !ok {
		return User{}, ErrNotFound
	}

	if inp.Name != "" {
		u.Name = inp.Name
	}
	if inp.Email != "" {
		u.Email = inp.Email
	}
	u.UpdatedAt = time.Now().UTC()

	s.users[id] = u
	return u, nil
}

// Delete removes the User with the given id from the store.
// Returns ErrInvalidID on empty id, or ErrNotFound when no match exists.
func (s *Store) Delete(id string) error {
	if id == "" {
		return ErrInvalidID
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, ok := s.users[id]; !ok {
		return ErrNotFound
	}

	delete(s.users, id)
	return nil
}
