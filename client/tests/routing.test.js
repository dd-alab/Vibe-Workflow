import { describe, expect, it } from "vitest";

import nextConfig from "../next.config.mjs";


describe("API routing", () => {
  it("proxies API calls to the local backend by default", async () => {
    const [apiRewrite] = await nextConfig.rewrites();

    expect(apiRewrite).toEqual({
      source: "/api/:path*",
      destination: "http://localhost:8000/api/:path*",
    });
  });
});
