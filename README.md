# Skills — Introduction to GitHub

> A hands-on introduction to the core GitHub workflow: branches, commits, pull requests, and reviews.

---

## Table of Contents

- [About](#about)
- [Getting Started](#getting-started)
- [Workflow Overview](#workflow-overview)
- [Contributing](#contributing)
- [License](#license)

---

## About

This project is designed to help new GitHub users learn the fundamentals of collaborative development using GitHub. By working through the exercises in this repository you will practise:

- Creating and switching between **branches**
- Making **commits** with clear messages
- Opening and reviewing **pull requests**
- Merging changes back into the main branch

---

## Getting Started

### Prerequisites

- A free [GitHub account](https://github.com/join)
- [Git](https://git-scm.com/downloads) installed on your machine (or use the GitHub web UI)

### Clone the repository

```bash
git clone https://github.com/MinnMinn/skills-introduction-to-github.git
cd skills-introduction-to-github
```

### Create your own branch

```bash
git checkout -b my-first-branch
```

Make a small change (e.g. add your name to a file), commit it, push, and open a pull request — that's the whole workflow!

```bash
git add .
git commit -m "feat: add my name to contributors"
git push origin my-first-branch
```

Then visit the repository on GitHub and click **"Compare & pull request"**.

---

## Workflow Overview

```
main
 └── my-feature-branch   ← create a branch
       ├── commit 1       ← make changes & commit
       └── commit 2
             └── Pull Request → review → merge back to main
```

| Step | Action | Git / GitHub |
|------|--------|--------------|
| 1 | Isolate your work | `git checkout -b <branch>` |
| 2 | Save a snapshot | `git commit -m "message"` |
| 3 | Share your work | `git push origin <branch>` |
| 4 | Request a review | Open a Pull Request on GitHub |
| 5 | Merge | Click **Merge pull request** |

---

## Contributing

Contributions, improvements, and questions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

---

## License

This project is released under the [MIT License](LICENSE).
