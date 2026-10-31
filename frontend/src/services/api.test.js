import assert from "node:assert/strict";
import test from "node:test";

import { apiUrl } from "./api.js";

test("keeps relative API paths for local Vite proxying when no API base is configured", () => {
  assert.equal(apiUrl("/api/research"), "/api/research");
});
