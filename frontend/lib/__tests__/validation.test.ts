import { describe, expect, it } from "vitest";
import { validateInputs } from "@/lib/validation";

const pdf = (bytes: number) => new File([new Uint8Array(bytes)], "cv.pdf", { type: "application/pdf" });

describe("validateInputs", () => {
  it("validates JD length and file type/size", () => {
    expect(validateInputs({ jd: "short", file: pdf(10) }).jd).toMatch(/300/);
    expect(validateInputs({ jd: "x".repeat(20001), file: pdf(10) }).jd).toMatch(/20,000/);
    expect(validateInputs({ jd: "x".repeat(300), file: new File(["x"], "a.png", { type: "image/png" }) }).file).toMatch(/PDF or DOCX/);
    expect(validateInputs({ jd: "x".repeat(300), file: pdf(6 * 1024 * 1024) }).file).toMatch(/5 MB/);
    expect(validateInputs({ jd: "x".repeat(300), file: null }).file).toMatch(/Upload/);
    expect(validateInputs({ jd: "  " + "x".repeat(300) + "  ", file: pdf(10) })).toEqual({});
  });
  it("accepts docx by extension even without a MIME type", () => {
    expect(validateInputs({ jd: "x".repeat(300), file: new File(["x"], "cv.DOCX") })).toEqual({});
  });
});
