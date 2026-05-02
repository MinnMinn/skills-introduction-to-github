# User Guide — Feature Submission

## Overview

This guide explains how to submit a new feature request using the application's submission form. The form is powered by the **Submit Button** (described in [`../frontend/button.md`](../frontend/button.md)) which communicates with the backend API (described in [`../backend/api.md`](../backend/api.md)).

---

## Prerequisites

Before you can submit a feature request you must:

1. **Have an account** — Register at the Sign-Up page if you don't have one.
2. **Be signed in** — The Submit Button requires a valid session. If you are not signed in you will see an *Unauthorised* error (see [Troubleshooting](#troubleshooting) below).

---

## Step-by-Step Instructions

### Step 1 — Open the Submission Form

Navigate to **Dashboard → New Feature** in the top navigation bar. The submission form will load in the main content area.

### Step 2 — Fill in the Details

| Field | Required | Description |
|-------|----------|-------------|
| **Title** | ✅ Yes | A short, descriptive name for your feature (1–120 characters). |
| **Description** | ❌ No | A longer explanation of what the feature should do (max 1 000 characters). |
| **Tags** | ❌ No | Up to 10 tags to help categorise your request (e.g. `ui`, `performance`). |

### Step 3 — Click Submit

Click the **Submit** button at the bottom of the form. The button will show a loading spinner while your request is being processed (see [frontend/button.md](../frontend/button.md) for the button's loading states).

### Step 4 — Confirm Success

On success, a green confirmation banner will appear at the top of the page:

> ✅ **Feature submitted!** Your request has been queued for review.

Your submission is now saved and will appear in the **My Submissions** list within a few seconds.

---

## What Happens Next?

After you submit, the backend (see [backend/api.md](../backend/api.md)) processes your request:

1. Your data is validated and stored with the status **"Pending Review"**.
2. A member of the team will review your submission and update its status to **Approved** or **Declined**.
3. You will receive an email notification when the status changes.

---

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| Button is greyed out / unclickable | A request is already in flight | Wait for the current request to finish |
| *"Unauthorised"* error below the button | Session has expired | Sign out, sign back in, and try again |
| *"Title is required."* error | Title field was left blank | Fill in the **Title** field and resubmit |
| *"An unexpected error occurred."* | Server-side issue | Wait a moment and try again; contact support if it persists |
| Button stays in loading state | Network connectivity issue | Check your internet connection and refresh the page |

---

## Keyboard & Accessibility

- Press **Tab** to move focus to the Submit Button.
- Press **Enter** or **Space** to activate the button when it has focus.
- Screen readers will announce *"Submitting…"* while the request is in progress.

For the full accessibility specification see [frontend/button.md → Accessibility](../frontend/button.md#accessibility).

---

## See Also

- [Submit Button — UI Component](../frontend/button.md)
- [Feature Submit — API Endpoint](../backend/api.md)
