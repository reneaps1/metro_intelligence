import { afterEach, describe, expect, it } from "vitest";
import { BRAND_STORAGE_KEY, buildVariant, isPreviewing, resolveVariant, watermarkUrl } from "./brand";

afterEach(() => window.localStorage.removeItem(BRAND_STORAGE_KEY));

describe("demo brand variant", () => {
  it("defaults to the build variant, then b", () => {
    expect(buildVariant("C")).toBe("c");
    expect(buildVariant("nope")).toBe("b");
    expect(buildVariant(undefined)).toBe("b");
  });

  it("lets ?marca= preview a proposal and remembers it", () => {
    expect(isPreviewing()).toBe(false);
    expect(resolveVariant("?marca=a")).toBe("a");
    expect(isPreviewing()).toBe(true);
    expect(resolveVariant("")).toBe("a");
    expect(resolveVariant("?marca=zzz")).toBe("a");
  });

  it("escapes viewer text inside the watermark", () => {
    const url = decodeURIComponent(watermarkUrl(["DEMO", "<x>&"], 0.1));
    expect(url).toContain("&#60;x&#62;&#38;");
    expect(url).not.toContain("<x>");
  });
});
