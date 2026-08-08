# Data dictionary — `extensions.jsonl` / `extensions.csv`

One row per distinct extension. Same fields in both files.

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `publisher.name`, the Marketplace's unique identifier |
| `publisher` | string | Publisher id |
| `publisher_display` | string | Publisher display name |
| `name` | string | Extension id, unique across the whole Marketplace (not per publisher) |
| `display` | string | Extension display name |
| `category` | string | The category under which this extension was first seen. Extensions may belong to several; only one is recorded |
| `installs` | int | **Install count as reported by the Marketplace.** Installs, not active users, and not retained users |
| `updates` | int | Update count |
| `downloads` | int | Raw VSIX download count. Includes CI, mirrors and bots — `installs` is the better demand signal |
| `rating` | float | Mean rating, 0 if unrated |
| `ratings` | int | Number of ratings |
| `trending_weekly` | float | Marketplace's weekly trending score |
| `released` | date | First release, `YYYY-MM-DD` |
| `updated` | date | Last version publish date |
| `version` | string | Latest version string |

**A row is not a product's whole history.** `installs` is cumulative since release, so an old
abandoned extension can outrank an excellent new one. Read `updated` alongside it.

**`downloads` > `installs` is normal** and is not an error: automated fetches inflate it.
