# Glossary

These are the terms used across the ADORE web interface and in these help topics.

## Terms {#terms}

| Term | Meaning |
|---|---|
| Job | One repository issue being worked on and checked in an isolated environment. |
| Enrolled project | An existing repository configured on the ADORE host, with access granted to its team. |
| Monitoring | A project's setting for picking up new tickets, shown as **Active** or **Paused**. Administrators change it with **Pause monitoring** and **Activate monitoring** on the project's Summary tab. |
| Pickup stopped | ADORE stops picking up new issues for this project. This does not pause an active job. It is the state Monitoring shows as **Paused**. |
| Ticket | An issue on the forge. ADORE picks it up when it carries the project's ready label and a priority label, is not held or excluded, and has acceptance criteria if the project requires them. |
| Coding agent / Executor | The AI command-line tool that does the work for a job in an isolated environment: Pi, the only coding agent ADORE runs. It has no forge credentials and never commits, pushes, opens or merges. |
| Model | The model ID within the chosen provider, for example gpt-5.4 for OpenAI. It is set with the provider in Settings → Agent and model, and estimated prices belong to an executor and model pair. |
| AEGIS | The workflow installed in the repository that frames, specifies, designs, builds and validates a change. ADORE conducts it one stage at a time (Frame, Specify, Design, Build, Validate) and publishes the approved result; a small change may skip Specify and Design. |
| Candidate | The validated result of a job that ADORE presents for approval, identified by a fingerprint and the target commit. Approval applies to that exact candidate and lapses if the candidate or its target branch changes. |
| Waiting for clarification | The agent needs an answer before continuing. Respond to its question in the repository issue. |
| Waiting for approval | The result is validated and waiting for a person to authorize publication. Approval is recorded on the forge for the current candidate. |
| Draft MR/PR | The merge request (GitLab) or pull request (GitHub, Gitea) that ADORE opens after approval, as a draft unless the project is set to publish a ready one. People review it. |
| Human review | An MR/PR is available for human review. Merge remains a human decision. |
| Revision round | One more pass of the coding agent on the same branch after a reviewer requests changes, or after failed CI checks when automatic repair is on. Rounds are limited by **Maximum revision rounds**, and each one needs a fresh approval before anything is published. |
| Forge | The hosting platform where tickets, labels, approvals and MR/PRs live: GitHub, GitLab or Gitea. |

> ADORE has no merge operation. Merging is always a person's decision on the forge.
