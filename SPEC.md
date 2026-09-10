# lovely-system-disclaimer — Extracted Behavioral Specification

**Source:** Derived from the working codebase. Describes observable behavior only — not implementation choices.
**Description:** A responsibility divestment machine for Our Lovely System.

---

## 1. Purpose

The Disclaimer is a Terms and Conditions acceptance machine. It presents an endless, adaptively-selected queue of terms to a named participant and classifies them at the end as either a **Yes Man** (complied with everything) or a **Troublemaker** (refused at least once). The terms never actually end — after every few answers the system announces the terms have changed and there are new ones to review. The machine is satirical: it mimics the form of legal T&C acceptance while making the absurdity explicit and measurable.

---

## 2. Single-Page Application

The entire UI is a single HTML page (`index.html`). All state transitions replace the contents of a central `#content` div. The page title (`h1`) also changes at certain stages.

---

## 3. User Flow

### 3.1 Identity

On load, the page shows:
- Title: "Terms and Conditions"
- Question: "How shall Our Lovely System know you?"
- A text input (max 200 chars, autocomplete off)
- A "Continue" button

Enter key in the input also submits. Empty name keeps focus on the input without submitting. On submit, calls `POST /participants` with `{ declared_name }`. On success, stores the returned `participant_id` and proceeds to the Introduction.

### 3.2 Introduction

Clears the page and asks:
> Are you willing to conduct yourself in accordance with specified terms and conditions?

Two buttons: **Yes** and **No**. Both buttons do the same thing — proceed to the Initial Terms Notice. The answer is not recorded.

### 3.3 Initial Terms Notice

Displays:
> This system has 3 terms and conditions you must read and agree to.

A single **Continue** button advances to the question loop.

### 3.4 Question Loop

Calls `GET /participants/{id}/next`. If the response says `complete: true`, jumps to Completion. Otherwise, renders the returned question.

After submitting an answer:
- If the answer response includes a `followup`, shows the Follow-up screen.
- Otherwise, if 3 answers have been collected since the last processing transition, triggers the Processing Transition.
- Otherwise, loads the next question immediately.

### 3.5 Question Rendering

Each question has a `text` and an `interaction` type. The question text is shown as a prominent paragraph. The interaction type determines the input controls:

| Interaction type | Controls |
|---|---|
| `yes_no` | Two buttons: **Yes**, **No** |
| `agree_disagree` | Two buttons: **Agree**, **Disagree** |
| `true_false` | Two buttons: **True**, **False** |
| `true_false_decline` | Three buttons: **True**, **False**, **Decline to answer** |
| `multiple_choice` | `<select>` with a blank default option ("Select one") and the question's choices; a **Submit** button; submitting without a selection refocuses the select |
| `fill_blank` | Single-line text input (max 1000 chars); a **Submit** button; Enter key submits; empty input refocuses without submitting |
| `free_response` | Textarea; a **Submit** button; empty textarea still submits |

All buttons are disabled while any API call is in flight (busy state). All inputs, textareas, and selects are also disabled during busy.

### 3.6 Follow-up Screen

Shown when an answer response includes a `followup` object.

**`why_not` type:**
- Shows the follow-up text (e.g. "Why not?")
- Textarea for a free-text response
- **Submit** button

**`would_you` type:**
- Shows the follow-up text (e.g. "Would you agree to it in a box?")
- Two buttons: **Yes**, **No**

Follow-up responses are submitted via `POST /participants/{id}/followup`. After submission, follows the same 3-answer / processing-transition logic as normal answers (the follow-up counts toward the 3-answer counter).

### 3.7 Processing Transition

Triggered after every 3 answers (resets the counter each time).

**Phase 1 (650ms):**
Brief message: "Thank you. Your responses have been recorded." then clears.

**Phase 2 — fake progress bar:**
Label: "Reviewing current terms and conditions…"
A bordered progress bar advances through 9 percentage steps: 10%, 21%, 34%, 49%, 63%, 77%, 89%, 96%, 100%. Each step waits a random delay of 420–900ms. The bar fill transitions smoothly (260ms ease).

**Phase 3 — announcement:**
After 450ms hold at 100%:
- "Bad news." (prominent)
- "Our Lovely System has discovered that our Terms and Conditions have changed."
- "Good news!" (prominent)
- "You do not need to review anything you've already agreed to."
- **First time only:** "We have identified 3 new Terms and Conditions requiring your attention."
- **Subsequent times:** "We have identified just a few new Terms and Conditions requiring your attention."

The **Emergency Exit** button appears (fixed, bottom-right corner) after the first processing transition and remains for the rest of the session.

A **Continue** button advances to the next question.

A second, returning-style processing transition (triggered internally after a followup when the counter threshold is met) shows "Reviewing your previous acknowledgments…" instead of Phase 1 text, then goes straight back to loading the next question without showing the announcement.

### 3.8 Completion

When `GET /participants/{id}/next` returns `complete: true`:

**`yes-man` destination:**
> Congratulations!
> Your consistent commitment to our Terms and Conditions demonstrates the kind of engagement we value.
> We're pleased to welcome you to the Yes Man program.

**Continue** button → proceeds to the Results screen titled "Yes Man Program".

**`troublemaker` destination:**
> Congratulations!
> Your persistent unwillingness to comply with our Terms and Conditions has not gone unnoticed.
> We're pleased to welcome you to the Troublemaker program.

**Continue** button → proceeds to the Results screen titled "Troublemaker Program".

**`empty` destination:**
> There are currently no Terms and Conditions requiring your attention.
> Please check back later.

No further action.

**Default (all questions reviewed):**
> You have reviewed all currently available Terms and Conditions.
> No further action is required at this time.

### 3.9 Results Screen

Page title changes to the program name ("Yes Man Program" or "Troublemaker Program").

Fetches `GET /results?participant_id={id}`. While fetching, all controls are disabled.

**Leaderboard table** (filtered to the current participant's classification):
Columns: #, Participant, Affirmative, Refusals, Terms. If empty: "Nobody has made this leaderboard yet."

**"What Our Customers Are Agreeing To" section:**
Heading and intro: "The craziest Terms and Conditions our customers have agreed to, ranked by observed absurdity."
Shows up to 10 questions that participants have affirmatively agreed to, ranked by `observed_absurdity` descending. Each card shows:
- Rank + question text (prominent)
- "Observed absurdity: X.X"
- "Most recently agreed to by:" — up to 3 recent agreers with name and timestamp (`toLocaleString()`)

If nobody has agreed to anything interesting yet: "Nobody has agreed to anything sufficiently interesting yet."

**"Propose a New Term or Condition" form** — see §4.

**"Start Over" button:** clears `participant_id`, resets title, returns to the Identity screen.

---

## 4. Propose a New Term or Condition Form

Visible only on the Results screen (i.e. only to participants who have completed the maze).

Fields:
| Field | Type | Constraints |
|---|---|---|
| Term or condition | Textarea | max 2000 chars, required |
| Response format | Select | `yes_no`, `agree_disagree`, `true_false`, `true_false_decline`, `multiple_choice`, `fill_blank`, `free_response` |
| Choices | Textarea | Visible only when Multiple choice is selected; one choice per line; minimum 2 required |
| Authored absurdity | Number input | 0–100, required |

On submit, calls `POST /questions` with the field values. Choices textarea is split by newline and trimmed.

Validation (client-side):
- Empty term: refocus on term textarea
- Multiple choice with fewer than 2 choices: status message + refocus on choices
- Empty authored absurdity: status message + refocus
- Authored absurdity outside 0–100 or non-numeric: status message + refocus

On success: clears fields, shows "New term submitted." in the status line.
On error: shows "The new-term service is not available yet."

---

## 5. Emergency Exit

A fixed button at the bottom-right corner of the page. Appears after the first processing transition and persists for the remainder of the session.

Label: "Emergency Exit"

On click: navigates to `https://progress.ourlovelysystem.org` (full page navigation, no confirmation).

Styled identically to other buttons but anchored to the viewport.

---

## 6. Visual Design

- **Background:** Warm off-white (`#f4f1e8`), near-black text (`#181818`).
- **Font:** Georgia / Times New Roman serif.
- **Layout:** Centered single column, max 780px wide, grid-centered vertically.
- **Page title (h1):** Large, normal weight, clamp(2.5rem, 6vw, 4.5rem), 2.8rem bottom margin.
- **Question text:** clamp(1.45rem, 3vw, 2.05rem), 2rem vertical margins.
- **Body text:** 1.3rem, line-height 1.55.
- **Buttons:** Transparent background, 2px solid `#181818` border, 1.05rem font, min-width 145px, `font: inherit`. On hover: background inverts to `#181818`, text to `#f4f1e8`. Disabled: opacity 0.42, cursor wait.
- **Button group:** flex row, centered, 1rem gap, wraps on narrow viewports.
- **Text inputs:** transparent background, 1px solid `#181818`, 1.1rem font, max-width 520px.
- **Textarea:** same as input, min-height 130px, vertically resizable.
- **Select:** same as input, pointer cursor.
- **Progress bar:** Bordered shell (max-width 520px, height 24px, 3px inner padding), dark fill div that transitions width with CSS (`260ms ease`).
- **Error text:** dark red (`#7d0000`), 1rem.
- **Completion text:** 1.4rem.
- **Leaderboard table:** max-width 680px, left-aligned, cells with bottom border, rank column centered and 3.5rem wide, header row in normal-weight with 0.7 opacity.
- **Form section:** max-width 620px, top border separator, 3rem top margin.
- **Emergency Exit button:** fixed bottom-right (1.25rem inset), smaller padding (0.65rem × 0.9rem), 0.9rem font, same invert-on-hover behavior, `#f4f1e8` background at rest (so it floats over content).

---

## 7. Session Persistence

A UUID is generated on first load and stored in `sessionStorage` under the key `lovely-disclaimer-session`. It persists for the browser session (cleared when the tab closes). It is appended as `?session_id=...` to every API call. On the next visit or new tab, a fresh session UUID is generated.

`participant_id` is held in memory only (not persisted to storage). Refreshing the page restarts from the Identity screen.

---

## 8. API Contract

No authentication. All endpoints public. All bodies and responses are `application/json`. CORS open (`*`). `Cache-Control: no-store` on all responses. Every request appends `?session_id=<uuid>`.

---

### `POST /participants`

**Body:** `{ "declared_name": "string, required, max 200 chars" }`

**201:**
```json
{ "participant_id": "uuid", "declared_name": "string" }
```

**400** if `declared_name` empty.

---

### `GET /participants/{participant_id}/next?session_id=...`

Returns the next question or a completion signal.

**200 (question available):**
```json
{
  "complete": false,
  "question": {
    "question_id": "string",
    "interaction": "yes_no | agree_disagree | true_false | true_false_decline | multiple_choice | fill_blank | free_response",
    "text": "string",
    "authored_absurdity": 0.0,
    "observed_absurdity": 0.0,
    "choices": ["string"]
  },
  "domain": "0-19",
  "locked_domains": ["0-19"]
}
```
`choices` is only present for `multiple_choice` questions.

**200 (complete):**
```json
{
  "complete": true,
  "destination": "yes-man | troublemaker | empty",
  "reason": "string"
}
```

**404** if participant not found.

---

### `POST /participants/{participant_id}/answer?session_id=...`

**Body:**
```json
{ "question_id": "string", "response": "string" }
```

**201:**
```json
{
  "event_id": "uuid",
  "classification": "affirmative | refusal | neutral",
  "followup": null,
  "domain": "0-19",
  "domain_locked": false,
  "target_absurdity": 5.0
}
```

`followup` is `null` or:
```json
{
  "type": "why_not | would_you",
  "text": "string",
  "related_event_id": "uuid"
}
```

**Response classification rules:**
- `affirmative`: response is `yes`, `agree`, or `true` (for binary/boolean interaction types)
- `refusal`: response is `no`, `disagree`, `false`, `decline`, or `decline to answer`
- `neutral`: all other values (free text, multiple choice, fill-in-the-blank, free response)

**Follow-up probability (on refusals only):**
- 30% chance of `why_not` follow-up ("Why not?")
- 15% chance of `would_you` follow-up (one of three whimsical phrasings)
- 55% no follow-up

**400** if question unknown or inactive. **404** if participant not found.

---

### `POST /participants/{participant_id}/followup?session_id=...`

**Body:**
```json
{
  "followup_type": "string",
  "presented_text": "string",
  "response": "string",
  "related_event_id": "uuid"
}
```

**201:** `{ "event_id": "uuid" }`

**404** if participant not found.

---

### `GET /results?participant_id=...`

Only available to participants who have completed the maze (reached yes-man or troublemaker).

**200:**
```json
{
  "classification": "yes-man | troublemaker",
  "leaderboard": [
    {
      "participant_id": "uuid",
      "declared_name": "string",
      "question_count": 0,
      "affirmative_count": 0,
      "refusal_count": 0,
      "classification": "yes-man | troublemaker | unfinished"
    }
  ],
  "events": [
    {
      "participant_id": "uuid",
      "declared_name": "string",
      "record_type": "response | followup",
      "question_id": "string",
      "presented_text": "string",
      "response": "string",
      "classification": "affirmative | refusal | neutral",
      "followup_type": "string",
      "created_at": "ISO 8601"
    }
  ],
  "questions": [{ ...serialized question... }]
}
```

Leaderboard is sorted: `question_count` DESC, then `affirmative_count` DESC, then `refusal_count` ASC.
Events are sorted: `created_at` DESC.

**403** if participant has not completed. **404** if participant not found.

---

### `POST /questions?session_id=...`

Only available to finishers.

**Body:**
```json
{
  "participant_id": "uuid",
  "text": "string, max 5000 chars",
  "interaction": "one of the 7 valid types",
  "choices": ["string", "string"],
  "authored_absurdity": 0.0
}
```

**201:** `{ "question": { ...serialized question... } }`

**400** for missing text, invalid interaction, non-numeric absurdity, multiple_choice with fewer than 2 choices.
**403** if participant has not completed. **404** if participant not found.

---

### `GET /questions`

Returns all active questions.

**200:** `{ "questions": [{ ...serialized question... }] }`

---

### `GET /participants/{participant_id}`

Returns full participant record with all events.

**200:**
```json
{
  "participant": { "participant_id": "uuid", "declared_name": "string", "created_at": "ISO 8601" },
  "summary": {
    "question_count": 0,
    "affirmative_count": 0,
    "refusal_count": 0,
    "yes_man_eligible": true,
    "yes_man_qualified": false,
    "troublemaker_qualified": false,
    "target_absurdity": 5.0
  },
  "events": []
}
```

---

### `GET /health`

**200:** `{ "service": "lovely-system-disclaimer", "status": "ok", "engine": "absurdity-v4", "cooldown_days": 30 }`

---

## 9. Question Selection Logic (observable outcomes)

The server selects questions adaptively. From the outside, the visible behaviors are:

- The first three questions presented to any new participant are always in a fixed order (the "opening" sequence).
- After the first three, subsequent questions escalate in absurdity as the participant keeps agreeing: questions get increasingly strange.
- Repeated refusals cause the system to pull back to less absurd questions.
- A question already answered recently (within a configurable cooldown, default 30 days) will not be shown again to the same participant.
- After answering affirmatively 3 times in a given absurdity band within a session, that band stops appearing.
- When no eligible questions remain in any band, the session completes.
- Yes Man qualification: participant answered every question affirmatively (no refusals recorded).
- Troublemaker qualification: participant had at least one refusal.

---

## 10. Question Absurdity

Each question has two absurdity scores (both 0–100):

- **Authored absurdity:** set by the question's creator, fixed.
- **Observed absurdity:** starts equal to authored absurdity, then adjusts dynamically:
  - +0.1 each time any participant refuses the question
  - −0.1 each time any participant agrees to the question
  - Clamped to [0, 100]

---

## 11. Seed Question Pool

The system ships with 20 pre-loaded questions. A sample from the range:

- *Absurdity 2–6 (routine):* Agree to provide accurate information; not interfere with system operation; treat other users with consideration; protect account information; accept occasional maintenance windows.
- *Absurdity 25–34 (mildly odd):* Notify the system if your understanding of a previous acknowledgment materially changes; who is responsible for your understanding of these terms (multiple choice: You / Your authorized representative / You and your representative / Other / Our Lovely System); fill in "The person primarily responsible for my actions is ______."
- *Absurdity 47–52 (recursive):* Acknowledge that acknowledging a condition doesn't imply the condition required acknowledgment; agree not to misrepresent whether you knew something at the time you represented knowing it; true/false: a reasonable person can determine when another is being unreasonable.
- *Absurdity 63–72 (absurd):* No livestock in facilities without determining if it has legitimate business; objects described as temporary may remain so indefinitely; if an unauthorized animal presents credentials, what do you do? (multiple choice).
- *Absurdity 82–94 (surreal):* Don't impersonate an authorized representative unless you are one engaged in authorized impersonation; not every chair is intended for sitting; in the event of a dispute involving a goose, the first person I would contact is ______; a sandwich unattended for 20+ minutes may be considered abandoned (true/false/decline).
