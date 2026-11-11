import { describe, expect, it } from "vitest";
import { buildVariant, watermarkUrl } from "./brand";

describe("demo brand variant", () => {
  it("is fixed at build time and defaults to the personal watermark (b)", () => {
    expect(buildVariant("C")).toBe("c");
    expect(buildVariant("nope")).toBe("b");
    expect(buildVariant(undefined)).toBe("b");
  });

  it("escapes viewer text inside the watermark", () => {
    const url = decodeURIComponent(watermarkUrl(["DEMO", "<x>&"], 0.1));
    expect(url).toContain("&#60;x&#62;&#38;");
    expect(url).not.toContain("<x>");
  });
});
