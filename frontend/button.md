# Submit Button — UI Component

## Overview

The **Submit Button** is the primary call-to-action element that triggers the feature workflow. When clicked, it sends a request to the backend API and displays real-time feedback to the user.

## Related Resources

- 🔌 **Backend endpoint** — see [`../backend/api.md`](../backend/api.md) for the API contract this button calls.
- 📖 **End-user instructions** — see [`../docs/user-guide.md`](../docs/user-guide.md) for how users are expected to interact with this button.

---

## Component Specification

### HTML / JSX

```jsx
<button
  id="submit-feature-btn"
  className="btn btn-primary"
  onClick={handleSubmit}
  disabled={isLoading}
  aria-label="Submit"
>
  {isLoading ? "Submitting…" : "Submit"}
</button>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `onClick` | `() => void` | — | Callback fired when the button is clicked. Should call `POST /api/feature/submit` (see [backend/api.md](../backend/api.md)). |
| `disabled` | `boolean` | `false` | Disables the button while a request is in-flight. |
| `isLoading` | `boolean` | `false` | When `true`, replaces the label with a spinner and disables the button. |

### States

| State | Visual Treatment |
|-------|-----------------|
| Default | Solid primary colour, full opacity |
| Hover | Slight darkening (`brightness: 0.9`) |
| Disabled / Loading | 50 % opacity, `cursor: not-allowed`, spinner icon |
| Success | Brief green flash before returning to default |
| Error | Brief red flash; error message shown below button |

---

## Behaviour

1. User clicks the button.
2. The component sets `isLoading = true` and fires a `POST` request to `/api/feature/submit` (documented in [backend/api.md](../backend/api.md)).
3. On **success** (HTTP `200`): display a success toast, reset the form.
4. On **error** (HTTP `4xx` / `5xx`): display the `error.message` field from the response body beneath the button.
5. In all cases, `isLoading` is reset to `false` after the response is received.

---

## Accessibility

- Must be focusable via keyboard (`Tab`).
- Must announce loading state via `aria-busy` when `isLoading` is `true`.
- Colour contrast ratio must be ≥ 4.5 : 1 (WCAG AA).

---

## See Also

- [Backend API reference](../backend/api.md)
- [User Guide](../docs/user-guide.md)
