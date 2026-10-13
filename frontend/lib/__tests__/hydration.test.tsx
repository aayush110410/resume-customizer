import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { InputPanel } from "@/components/input/InputPanel";
import { Sidebar } from "@/components/Sidebar";

const button = (html: string, label: string) => {
  const m = html.match(new RegExp(`<button[^>]*>(?:(?!</button>).)*${label}(?:(?!</button>).)*</button>`, "s"));
  return m?.[0] ?? "";
};

describe("server-rendered controls before hydration", () => {
  it("are disabled, so an early click is never silently lost or turned into a native form submit", () => {
    const form = renderToString(<InputPanel />);
    expect(button(form, "Try a sample")).toContain("disabled");
    expect(button(form, "Loading")).toContain("disabled");
    const rail = renderToString(<Sidebar onNew={() => {}} onHowWeScore={() => {}} />);
    expect(button(rail, "New analysis")).toContain("disabled");
  });
});
