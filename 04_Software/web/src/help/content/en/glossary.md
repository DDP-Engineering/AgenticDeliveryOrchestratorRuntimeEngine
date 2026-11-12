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
| AEGIS | The workflow installed in the repository that frames, specifies, designs, builds and validates a change. ADORE conducts it one stage at a time (Frame, Specify, Design, Build, Validate) and publishes the validated result under the project policy; a small change may skip Specify and Design. |
| Candidate | The validated result identified by a fingerprint and target commit. If approval is required, it applies to this exact candidate. |
| Waiting for clarification | The agent needs an answer before continuing. Respond to its question in the repository issue. |
| Waiting for approval | The result is validated and waiting for a person to authorize publication. Approval is recorded on the forge for the current candidate. |
| Draft MR/PR | The merge or pull request ADORE opens after validation and any required approval. People review it. |
| Human review | An MR/PR is available for human review. Merge remains a human decision. |
| Revision round | Another agent pass after requested changes or failed CI. Each round repeats validation and follows the project approval policy. |
| Forge | The hosting platform where tickets, labels, approvals and MR/PRs live: GitHub, GitLab or Gitea. |

> ADORE has no merge operation. Merging is always a person's decision on the forge.
