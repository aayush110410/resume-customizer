import { describe, expect, it } from "vitest";
import { highlight } from "@/lib/highlight";

const hits = (text: string, terms: string[]) => highlight(text, terms).filter((s) => s.hit).map((s) => s.text);

describe("highlight", () => {
  it("marks JD terms case-insensitively, longest first, on word boundaries", () => {
    expect(hits("Built REST APIs in Spring Boot and Java on AWS", ["java", "Spring Boot", "spring", "aws"])).toEqual(["Spring Boot", "Java", "AWS"]);
    expect(hits("Used Golang and Go daily", ["go"])).toEqual(["Go"]);
    expect(hits("Shipped C++ and Node.js services", ["c++", "node.js"])).toEqual(["C++", "Node.js"]);
  });
  it("returns the text unchanged when nothing matches, and rebuilds the full string", () => {
    expect(highlight("Plain text", ["kafka"])).toEqual([{ text: "Plain text", hit: false }]);
    expect(highlight("Kafka and kafka", ["kafka"]).map((s) => s.text).join("")).toBe("Kafka and kafka");
  });
});
