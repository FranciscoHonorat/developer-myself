import { describe, expect, it } from "vitest";
import { makePlan } from "@/test/fixtures";
import { makeContent } from "@/test/render";
import { needsOnboarding } from "./needsOnboarding";

describe("needsOnboarding", () => {
  it("trilha vazia precisa do guia", () => {
    expect(needsOnboarding(makePlan({ contents: [] }))).toBe(true);
  });
  it("com conteúdo não precisa", () => {
    expect(needsOnboarding(makePlan({ contents: [makeContent()] }))).toBe(false);
  });
});
