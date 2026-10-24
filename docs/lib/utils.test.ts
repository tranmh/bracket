import { describe, expect, it } from "vitest";

import { cn } from "./utils";

describe("cn", () => {
  it("returns an empty string without arguments", () => {
    expect(cn()).toBe("");
  });

  it("joins plain class names with single spaces", () => {
    expect(cn("a", "b", "c")).toBe("a b c");
  });

  it("drops falsy values (undefined, null, false, 0, empty string)", () => {
    expect(cn("a", undefined, null, false, 0, "", "b")).toBe("a b");
  });

  it("supports conditional object syntax", () => {
    expect(cn({ active: true, disabled: false }, "base")).toBe("active base");
  });

  it("flattens nested arrays", () => {
    expect(cn(["a", ["b", { c: true, d: false }]], "e")).toBe("a b c e");
  });

  it("lets later conflicting tailwind classes win", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
    expect(cn("p-6", "pt-0")).toBe("p-6 pt-0");
    expect(cn("pt-0", "p-6")).toBe("p-6");
  });

  it("merges conflicting colour utilities but keeps unrelated ones", () => {
    expect(cn("bg-red-500 text-white", "bg-blue-500")).toBe(
      "text-white bg-blue-500",
    );
  });

  it("resolves conflicts that come from conditional objects", () => {
    expect(cn("text-sm", { "text-lg": true })).toBe("text-lg");
    expect(cn("text-sm", { "text-lg": false })).toBe("text-sm");
  });

  it("keeps variant-prefixed classes separate from the base class", () => {
    expect(cn("bg-primary", "hover:bg-primary/90")).toBe(
      "bg-primary hover:bg-primary/90",
    );
    expect(cn("hover:bg-accent", "hover:bg-primary")).toBe("hover:bg-primary");
  });

  it("trims and collapses surrounding whitespace", () => {
    expect(cn("  a   b ", " c")).toBe("a b c");
  });
});
