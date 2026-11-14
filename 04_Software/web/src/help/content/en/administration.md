# Administration

Administration covers user accounts, project access, system health and the record of changes. It is for administrators only: a Dev does not see the Administration menu, and a Dev who opens one of its addresses is taken to Overview.

> Everything on this page requires the Administrator role.


A recent heartbeat means the supervisor is available. **Busy** means a worker is executing a command, project poll or job; **Activity unknown** means activity evidence is unavailable. Projects progress independently, with parallel jobs up to each project’s limit. Configuration commands have a separate worker. Queued starts wait for capacity; authorized cancellation can reach active work.

## Users {#users}

Under **Administration**, open [Users](/admin/users). The page has an **Add user** panel and a **Users** list.

To create an account:

1. Choose **Add user** above the list to open the creation dialog. Enter the **Username** and **Password** (at least 8 characters), then fill **Repeat new password** with the same value. The eye buttons show or hide each field. Choose **Continue to access**. If you return via **Correct identity**, enter the confirmation again. The review omits the password.
2. Choose the **Role** and, for a Dev, the projects. **Admin** grants all current and future projects, system administration and costs. **Dev** grants only the projects you tick, each listed by name with its forge and repository path. To create a Dev with no project, tick **Create Dev without project access** on purpose.
3. Choose **Review account**, check the identity and exact access, then choose **Create reviewed account**. **Correct identity** and **Correct access** take you back without creating anything.

The account and its access are created together, or not at all. A duplicate username or a project that changed in the meantime rejects the request; correct it and review again.

In the **Users** list each account offers these actions.

- **Assigned projects** (Dev accounts): tick or untick projects, choose **Save**, compare **Before** and **After**, then choose **Apply reviewed access**. **Correct access** cancels the review.
- **Disable** or **Enable**: a disabled account cannot sign in and its sessions end. You cannot disable your own account, and the last active administrator cannot be disabled.
- **Reset password**: select the action on the account’s row. In the dialog, check the account name, enter a **New password** of at least 8 characters and fill **Repeat new password**. Use the eye buttons to show or hide each entry. Choose **Save** when they match, or **Close** to discard the draft. Saving ends the account’s sessions and requires a new password at its next sign-in. There is no email password recovery.

## Project access {#project-access}

A project's **Access** tab lists every developer account with **Has access** or **No access**. Choose **Grant access** or **Remove access** beside a developer, compare **Before** and **After**, then choose **Apply reviewed access**. The change leaves the developer's other projects alone and is recorded in Change history. The access list refreshes every 15 seconds while the browser tab is visible.

A developer with access sees the project and can start, retry or cancel its jobs. Administrators always have access.

## System status {#system-status}

Under **Administration**, open [System status](/admin/status). It refreshes by itself.

- **Control worker** shows **Ready** when idle, **Busy** while processing, **Activity unknown** when the activity evidence is missing, **Unavailable**, **Status check failed** or **Checking…**. A recent heartbeat does not confirm forge, executor or model reachability.
- **Storage** reads **Space available**, **Low disk space** or **Storage check failed**. It measures free disk space for the ADORE account database and each project's job state folder, grouped by physical volume. One shared disk gets a single line; several disks get a **Volume**, **Free** and **Status** table. Below 1 GiB free counts as low, and a failed measurement is never shown as free space.
- **Audit retention** sets how long change history is kept. The current limits (or **Unlimited**) appear above the form. Set **Keep for days** (whole days, 0 to 36500) and **Audit data limit (MiB)** (0 to 1024, fractions allowed) and choose **Save**. Zero or blank means unlimited. The two limits apply independently and the oldest events are removed first. The notice after saving reports how many events were deleted. The size limit counts stored audit text, not the database file on disk. Jobs, run journals and accounts are kept.

## Change history {#change-history}

Under **Administration**, open [Change history](/admin/audit) to see who changed what, when, and with what result. A project's **History** tab shows the same evidence for that project alone, together with its finished jobs. Both views refresh every 15 seconds while visible and keep your filters, page and open evidence. On the global Change history page, **Refresh** reloads the list immediately.

History identifies ticket and job targets separately from operation numbers. A failed operation is shown as **Failed**; a refused operation is **Rejected**. CLI deletions identify the actor as CLI and remain visible after the job is removed. An interrupted deletion stays **Uncertain** until its result is confirmed.

Filters:

- **Actor ID**: the number shown beside an account name.
- **Project**: any project, or **All projects**.
- **Change type**: the exact action code.
- **From (UTC)** includes its instant; **Until (UTC, exclusive)** does not.

Choose **Apply filters**; this returns to the first page. The page reports how many events matched, and **Rows per page** offers 10, 25, 50 or All with **Previous** and **Next**.

Each row shows **Who**, **What**, **When** and **Result**: **Prepared**, **Applied**, **Discarded**, **Rejected** or **Uncertain**. Prepared means a candidate was staged, not applied. **Uncertain** means the host could not confirm completion; inspect the real resource before recovering. **Evidence** opens a row below the event with **Before**, **After / candidate**, the **Operation**, and the **Base revision** and **Candidate revision** when recorded. **Before value not recorded** means unknown, not empty. Passwords and environment values are never shown.

Change history is kept indefinitely unless you set limits under [System status](#system-status). There is no download or export of change history. A Dev sees operational changes only for assigned projects; account, access, price and policy events stay with administrators.
