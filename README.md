# Introduction to GitHub

> A beginner-friendly repository that walks you through the core GitHub workflow — branching, committing, opening pull requests, and merging — all in one hands-on exercise.

---

## Table of Contents

- [About the Project](#about-the-project)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [License](#license)

---

## About the Project

**skills-introduction-to-github** is a guided exercise repository created to help new developers get comfortable with the fundamental GitHub workflow. By the end of the exercise you will have practised:

- Creating a **branch** to isolate your work
- Making a **commit** to save changes
- Opening a **pull request** to propose those changes
- **Merging** a pull request into the main branch

This repo is based on [GitHub Skills](https://skills.github.com/) and is designed to be completed entirely in the browser — no local tooling required.

---

## Getting Started

### Prerequisites

All you need is a free [GitHub account](https://github.com/join). No local installation is required.

### Running the exercise

1. **Fork or use this repository**
   - Click the green **"Use this template"** button (or fork it) to get your own copy.

2. **Follow the steps in order**
   - Open the [Issues tab](../../issues) and start with the first open issue.
   - Each issue contains step-by-step instructions.

3. **Create a branch**
   ```bash
   # If you prefer working locally, clone your copy first:
   git clone https://github.com/<your-username>/skills-introduction-to-github.git
   cd skills-introduction-to-github

   # Then create a new branch:
   git checkout -b my-first-branch
   ```

4. **Make a change and commit**
   ```bash
   # Edit or create a file, then stage and commit:
   git add .
   git commit -m "my first commit"
   git push origin my-first-branch
   ```

5. **Open a Pull Request** on GitHub and follow the automated feedback to complete the exercise.

---

## How to Contribute

Contributions are welcome! Here's how to get involved:

1. **Fork** the repository and create your branch from `main`:
   ```bash
   git checkout -b feature/your-improvement
   ```

2. **Make your changes** — fix a typo, improve the instructions, or add a new exercise step.

3. **Commit** with a clear, descriptive message:
   ```bash
   git commit -m "docs: clarify step 2 instructions"
   ```

4. **Push** your branch and open a **Pull Request** against `main`.

5. A maintainer will review your PR. Please:
   - Keep changes focused and minimal.
   - Follow the existing Markdown style.
   - Be respectful and constructive in all discussions (see [Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md)).

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

Copyright &copy; GitHub, Inc.
