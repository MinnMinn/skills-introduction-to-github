# skills-introduction-to-github

> A hands-on Go project demonstrating GitHub fundamentals — branching, pull requests, and clean code organisation — through a simple **User CRUD** implementation.

---

## 📦 Project Description

This repository is a beginner-friendly introduction to GitHub workflows.  
It ships a self-contained Go package (`user`) that implements full **Create / Read / Update / Delete** operations for a `User` entity using an in-memory, thread-safe store — no external dependencies required.

### Key features
| Feature | Details |
|---|---|
| `User` struct | `ID`, `Name`, `Email`, `CreatedAt`, `UpdatedAt` |
| `Store.Create` | Validates input, sets timestamps, rejects duplicate IDs |
| `Store.ReadByID` | Fetches a single user by ID |
| `Store.ReadAll` | Returns all stored users |
| `Store.Update` | Patches `Name` / `Email`; updates `UpdatedAt` |
| `Store.Delete` | Removes a user; returns `ErrNotFound` if absent |
| Thread safety | All methods guarded by `sync.RWMutex` |
| Sentinel errors | `ErrNotFound`, `ErrAlreadyExists`, `ErrInvalidID`, … |

---

## 🚀 Getting Started

### Prerequisites
- [Go 1.21+](https://go.dev/dl/)
- Git

### Clone & run tests

```bash
# 1. Clone the repository
git clone https://github.com/MinnMinn/skills-introduction-to-github.git
cd skills-introduction-to-github

# 2. Run all tests
go test ./...

# 3. Run tests with the race detector (recommended)
go test -race ./...

# 4. Run tests with verbose output
go test -v ./user/...
```

### Use the package in your own code

```go
package main

import (
    "fmt"
    "github.com/MinnMinn/skills-introduction-to-github/user"
)

func main() {
    store := user.NewStore()

    // Create
    u, _ := store.Create(user.User{
        ID:    "1",
        Name:  "Alice",
        Email: "alice@example.com",
    })
    fmt.Println("Created:", u.Name)

    // Read
    found, _ := store.ReadByID("1")
    fmt.Println("Found:", found.Email)

    // Update
    updated, _ := store.Update("1", user.UpdateInput{Name: "Alicia"})
    fmt.Println("Updated:", updated.Name)

    // Delete
    _ = store.Delete("1")
    fmt.Println("Deleted user 1")
}
```

---

## 🤝 How to Contribute

Contributions are welcome! Please follow these steps:

1. **Fork** this repository and create your feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes** — keep commits small and focused.
3. **Write or update tests** for any new behaviour.
4. **Run the test suite** and ensure it passes:
   ```bash
   go test -race ./...
   ```
5. **Open a Pull Request** against `main` with a clear title and description.

Please adhere to the existing code style and add comments for exported identifiers.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

© 2025 GitHub
