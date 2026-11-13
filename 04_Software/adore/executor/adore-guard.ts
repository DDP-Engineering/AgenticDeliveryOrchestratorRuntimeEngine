/*
 * Copyright (c) 2026 DDP Engineering
 * This software is licensed under the PolyForm Noncommercial License 1.0.0.
 * Commercial use requires a separate commercial license.
 * See the LICENSE.txt file for full license details.
 * SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
 */

/**
 * ADORE's Pi guard extension, loaded explicitly with `-e` for every Pi RPC run
 * in the executor image, so it applies without project trust.
 *
 * It blocks publication from the model's shell tools - `git push` and the
 * gh, glab and tea forge CLIs - before they run: Pi reports the attempt as a
 * failed tool call whose text starts with "ADORE blocks". ADORE publishes only
 * under the project policy. This is defence in depth: the real boundary is that no
 * forge credential is in the agent's environment.
 *
 * It also answers project trust with "no", so a repository's own `.pi`
 * extensions and skills never load.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const BLOCKED: Array<[RegExp, string]> = [
	[/\bgit\b[^\n;&|]*\bpush\b/i, "git push"],
	[/(^|[\s;&|(`$])(gh|glab|tea)(\.exe)?(\s|$)/i, "forge CLI"],
];

export default function (pi: ExtensionAPI) {
	pi.on("tool_call", async (event) => {
		if (event.toolName !== "bash" && event.toolName !== "powershell") return undefined;
		const command = String((event.input as { command?: unknown }).command ?? "");
		for (const [pattern, label] of BLOCKED) {
			if (pattern.test(command)) {
				return {
					block: true,
					reason: `ADORE blocks ${label}: publication is managed by ADORE under the project policy.`,
				};
			}
		}
		return undefined;
	});
	pi.on("project_trust", async () => ({ trusted: "no" }));
}
