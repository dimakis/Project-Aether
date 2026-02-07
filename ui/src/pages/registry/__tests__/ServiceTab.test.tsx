import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ServiceTab } from "../ServiceTab";
import type { Service } from "@/lib/types";

// Mock framer-motion for synchronous behavior
vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({
      children,
      ...props
    }: React.HTMLAttributes<HTMLDivElement> & { [key: string]: unknown }) => {
      const { initial, animate, exit, transition, ...rest } = props as Record<string, unknown>;
      return <div {...(rest as React.HTMLAttributes<HTMLDivElement>)}>{children}</div>;
    },
  },
}));

// Mock DataViewer
vi.mock("@/components/ui/data-viewer", () => ({
  DataViewer: () => <div data-testid="data-viewer" />,
}));

const makeService = (domain: string, service: string): Service => ({
  id: `${domain}.${service}`,
  domain,
  service,
  name: `${domain} ${service}`,
});

// Generate 25 unique domains
const manyDomains = Array.from({ length: 25 }, (_, i) => `domain${String(i).padStart(2, "0")}`);
const manyServices = manyDomains.map((d) => makeService(d, "test"));

describe("ServiceTab", () => {
  describe("expandable domain filter", () => {
    it("shows 'Show all' button when more than 15 domains", () => {
      render(
        <ServiceTab
          services={manyServices}
          domains={manyDomains}
          isLoading={false}
          searchQuery=""
        />,
      );
      expect(screen.getByRole("button", { name: /show all/i })).toBeInTheDocument();
    });

    it("does not show 'Show all' button when 15 or fewer domains", () => {
      const fewDomains = manyDomains.slice(0, 10);
      const fewServices = manyServices.slice(0, 10);
      render(
        <ServiceTab
          services={fewServices}
          domains={fewDomains}
          isLoading={false}
          searchQuery=""
        />,
      );
      expect(screen.queryByRole("button", { name: /show all/i })).not.toBeInTheDocument();
    });

    it("reveals all domains when 'Show all' is clicked", async () => {
      const user = userEvent.setup();
      render(
        <ServiceTab
          services={manyServices}
          domains={manyDomains}
          isLoading={false}
          searchQuery=""
        />,
      );
      // Last domain should NOT be visible initially
      expect(screen.queryByRole("button", { name: "domain24" })).not.toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: /show all/i }));

      // Now all domains should be visible
      expect(screen.getByRole("button", { name: "domain24" })).toBeInTheDocument();
      // Button should now say "Show less"
      expect(screen.getByRole("button", { name: /show less/i })).toBeInTheDocument();
    });

    it("collapses domains when 'Show less' is clicked", async () => {
      const user = userEvent.setup();
      render(
        <ServiceTab
          services={manyServices}
          domains={manyDomains}
          isLoading={false}
          searchQuery=""
        />,
      );
      // Expand
      await user.click(screen.getByRole("button", { name: /show all/i }));
      // Collapse
      await user.click(screen.getByRole("button", { name: /show less/i }));

      expect(screen.queryByRole("button", { name: "domain24" })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: /show all/i })).toBeInTheDocument();
    });
  });
});
