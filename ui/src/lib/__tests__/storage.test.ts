import { describe, it, expect } from "vitest";
import { autoTitle, type DisplayMessage } from "../storage";

/** Helper to create a minimal messages array with one user message. */
function msgs(content: string): DisplayMessage[] {
  return [{ role: "user", content }];
}

describe("autoTitle", () => {
  it("returns 'New Chat' when there are no user messages", () => {
    expect(autoTitle([])).toBe("New Chat");
    expect(
      autoTitle([{ role: "assistant", content: "Hello!" }]),
    ).toBe("New Chat");
  });

  it("uses the full message when it is short enough", () => {
    expect(autoTitle(msgs("Turn on the lights"))).toBe(
      "Turn on the lights",
    );
  });

  it("summarises long messages instead of raw truncation", () => {
    const title = autoTitle(
      msgs(
        "Create an automation that turns on the living room lights when the sun sets and turns them off at midnight every day",
      ),
    );
    // Should be a concise summary, not a raw 40-char cut
    expect(title.length).toBeLessThanOrEqual(60);
    expect(title).not.toContain("...");
    // Should preserve meaningful keywords
    expect(title.toLowerCase()).toMatch(/light|automation|living/);
  });

  it("strips leading filler phrases", () => {
    const fillers = [
      "Can you create an automation for motion lights",
      "I want to set up a bedtime routine",
      "Please help me configure the thermostat",
      "Could you make a script to water the garden",
      "I'd like to build a scene for movie night",
    ];
    for (const f of fillers) {
      const title = autoTitle(msgs(f));
      // Should not start with "Can you", "I want to", "Please help me", etc.
      expect(title).not.toMatch(/^(can you|i want to|please help|could you|i'd like to)/i);
      // But should still carry meaning
      expect(title.length).toBeGreaterThan(3);
    }
  });

  it("handles questions naturally", () => {
    const title = autoTitle(
      msgs("What is the current temperature in the bedroom?"),
    );
    expect(title.length).toBeLessThanOrEqual(60);
    expect(title.toLowerCase()).toMatch(/temperature|bedroom/);
  });

  it("capitalises the first letter of the title", () => {
    const title = autoTitle(msgs("turn off all the lights in the house"));
    expect(title[0]).toBe(title[0].toUpperCase());
  });

  it("removes trailing punctuation for a clean title", () => {
    const title = autoTitle(msgs("What sensors do I have?"));
    expect(title).not.toMatch(/[?!.,;:]$/);
  });

  it("uses first user message even when there are multiple messages", () => {
    const messages: DisplayMessage[] = [
      { role: "user", content: "Set up a morning routine" },
      { role: "assistant", content: "Sure! Here's a plan..." },
      { role: "user", content: "Add a condition for weekdays only" },
    ];
    const title = autoTitle(messages);
    expect(title.toLowerCase()).toContain("morning routine");
  });

  it("handles very short messages gracefully", () => {
    expect(autoTitle(msgs("Hi"))).toBe("Hi");
    expect(autoTitle(msgs("Help"))).toBe("Help");
  });

  it("handles multiline messages by using only the first line", () => {
    const title = autoTitle(
      msgs("Set up garage door automation\n\nThe garage door sensor is binary_sensor.garage\nI want it to alert me if left open for 10 minutes"),
    );
    expect(title.length).toBeLessThanOrEqual(60);
    // Should focus on the first line's intent
    expect(title.toLowerCase()).toMatch(/garage/);
  });
});
