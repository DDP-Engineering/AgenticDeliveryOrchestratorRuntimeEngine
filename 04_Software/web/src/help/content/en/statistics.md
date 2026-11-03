# Statistics and costs

Statistics shows how much work ADORE did, what it consumed and how well the results held up. Costs are shown only to administrators, and estimated costs are not invoices.

## Reporting period and export {#period}

Open **Statistics** in the sidebar to see every project you can access, or open a project's **Statistics** tab to see that project alone. Both use the same layout: a **Reporting period** row above four tabs.

| Control | What it does |
|---|---|
| Project | Statistics page only. Administrators start with **All projects**; a Dev chooses among assigned projects. The project tab has no selector. |
| From and Through | The first and last day to include. **Through** includes that whole day. |
| Group by | **Day**, **Week** or **Month** buckets, used by the Trends tab and the exports. |
| All time | Clears both dates. Leaving both dates empty also means all time. |
| Export CSV | Opens a menu of downloads for the current project, dates and grouping. |

Dates and buckets use UTC unless the page address carries another time zone. The dates apply to every tab and every export. Changing the project keeps the period and the tab you are on.

The **Export CSV** menu offers **Project metrics**, **Project usage** and **Job consumption** for one project, or **All-project metrics**, **All-project usage** and **Job consumption** for **All projects**. It appears once the data has loaded. If a request fails, the page shows **Could not load data** and withholds totals and exports.

A dash means the value is unknown. Under a value, **Measured zero** means ADORE observed zero, **Not available** means nothing was recorded, and **Partial · known subtotal** means the figure covers only the usage that reported tokens.

## The four tabs {#tabs}

### Summary {#tab-summary}

Cards for **Started jobs**, **Completed jobs**, **Failed jobs**, **Input tokens**, **Output tokens** and **Known total tokens**. Completed counts every finished job whatever its outcome. The total needs both token directions to be known. Administrators also see **Reported cost** and **Estimated cost** cards. With **All projects**, a **Project comparison** table lists started, completed and failed jobs and average elapsed time per project, with the repository under each project name.

### Usage {#tab-usage}

**Usage by executor and model** starts with compact totals: usage events, input and output tokens, cache read and cache write, and job elapsed time (**Measured jobs**, **Average elapsed**, **Median elapsed**). The table below lists usage by date, executor and model; click a column heading to sort. With **All projects**, a per-project table follows. Administrators also see cost columns.

### Quality {#tab-quality}

**Delivery quality** shows **Reviewer rework**, **First validation pass**, **Merged without reviewer revision**, **Review still open**, **Stage failures** and **Operator retries**. Each rate shows its numerator and denominator. **Review still open** is the current state and ignores the period. Below are **MR/PR reviewer revisions** and **Pipeline repairs**, with a daily table of active days. With **All projects**, a per-project table adds review rounds.

### Trends {#tab-trends}

Usage coverage appears as a compact value. One table has a row per bucket (day, week or month) with started, completed and failed jobs as proportional bars, plus input and output tokens, and for administrators reported and estimated cost.

If the scope has no jobs yet, Quality and Trends say so and point you to Jobs → Tickets to start one.

## Reported and estimated costs {#costs}

Two cost figures are kept apart, and neither is a bill.

- **Reported cost** is what the executor reported, taken as observed evidence. If it reported none, the value reads **Not available**.
- **Estimated cost** is the recorded token counts multiplied by prices that administrators set. It is an estimate, not an invoice and not a spending cap.

Administrators record prices in a project's **Settings → Agent and model** under **Estimated prices**: choose **Effective from**, then enter **Input USD / 1M tokens** and **Output USD / 1M tokens** and **Save**. A price applies to the selected coding agent and its configured model, so set the model first. Each usage event is priced by the executor, model and the day it was consumed. Events with no matching price are counted as **Unpriced usage events** in the Usage totals.

> A price entered with an earlier effective date can change past estimates. Export a CSV if you need a point-in-time figure.

On the Quality tab, administrators also see **Cost per job with evidence**, per completed and per human-merged job, each with the number of jobs behind it.

## Who sees monetary values {#visibility}

| Role | Projects | Money |
|---|---|---|
| Administrator | **All projects** or any single project | Reported cost, Estimated cost, Unpriced usage events, cost per job, cost by revision, cost columns and the financial fields in CSV exports |
| Dev | Assigned projects only; no **All projects** | None. Devs see job counts, tokens, elapsed time and quality figures, never a financial field. |

Prices are set and visible only to administrators; a Dev's read-only Settings omit financial settings.
