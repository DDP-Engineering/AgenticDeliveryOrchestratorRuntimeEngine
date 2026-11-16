import { expect, request } from "@playwright/test";

/** Shut down the owned fixture gracefully so its temporary home is removed. */
export default async function teardown() {
  const api = await request.newContext({ baseURL: "http://127.0.0.1:18765", timeout: 5_000 });
  try {
    const response = await api.post("/__e2e__/shutdown", {
      headers: { "X-ADORE-E2E": "local-test" },
    });
    expect(response.status()).toBe(200);
    expect(await response.json()).toEqual({ test_server: "stopping" });
    await expect.poll(async () => {
      try {
        await api.get("/api/v1/health");
        return false;
      } catch {
        return true;
      }
    }, { timeout: 5_000 }).toBe(true);
  } finally {
    await api.dispose();
  }
}
