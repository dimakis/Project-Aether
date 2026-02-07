import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "../card";

describe("Card", () => {
  it("renders Card with all sub-components", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
          <CardDescription>Card description text</CardDescription>
        </CardHeader>
        <CardContent>
          <p>Card content</p>
        </CardContent>
      </Card>,
    );

    expect(screen.getByText("Card Title")).toBeInTheDocument();
    expect(screen.getByText("Card description text")).toBeInTheDocument();
    expect(screen.getByText("Card content")).toBeInTheDocument();
  });

  it("applies custom className to Card", () => {
    const { container } = render(
      <Card className="custom-card-class">
        <CardContent>Content</CardContent>
      </Card>,
    );
    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass("custom-card-class");
    expect(card).toHaveClass("rounded-xl", "border");
  });

  it("applies custom className to CardHeader", () => {
    const { container } = render(
      <Card>
        <CardHeader className="custom-header-class">
          <CardTitle>Title</CardTitle>
        </CardHeader>
      </Card>,
    );
    const header = container.querySelector(".custom-header-class");
    expect(header).toBeInTheDocument();
    expect(header).toHaveClass("flex", "flex-col", "space-y-1.5", "p-6");
  });

  it("renders CardTitle as h3", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Test Title</CardTitle>
        </CardHeader>
      </Card>,
    );
    const title = screen.getByRole("heading", { level: 3 });
    expect(title).toHaveTextContent("Test Title");
    expect(title).toHaveClass("font-semibold");
  });

  it("renders CardDescription as paragraph", () => {
    render(
      <Card>
        <CardHeader>
          <CardDescription>Test description</CardDescription>
        </CardHeader>
      </Card>,
    );
    const description = screen.getByText("Test description");
    expect(description.tagName).toBe("P");
    expect(description).toHaveClass("text-sm", "text-muted-foreground");
  });

  it("applies custom className to CardContent", () => {
    const { container } = render(
      <Card>
        <CardContent className="custom-content-class">
          Content
        </CardContent>
      </Card>,
    );
    const content = container.querySelector(".custom-content-class");
    expect(content).toBeInTheDocument();
    expect(content).toHaveClass("p-6", "pt-0");
  });

  it("forwards refs correctly", () => {
    const cardRef = vi.fn();
    const headerRef = vi.fn();
    const titleRef = vi.fn();
    const descriptionRef = vi.fn();
    const contentRef = vi.fn();

    render(
      <Card ref={cardRef}>
        <CardHeader ref={headerRef}>
          <CardTitle ref={titleRef}>Title</CardTitle>
          <CardDescription ref={descriptionRef}>Description</CardDescription>
        </CardHeader>
        <CardContent ref={contentRef}>Content</CardContent>
      </Card>,
    );

    expect(cardRef).toHaveBeenCalled();
    expect(headerRef).toHaveBeenCalled();
    expect(titleRef).toHaveBeenCalled();
    expect(descriptionRef).toHaveBeenCalled();
    expect(contentRef).toHaveBeenCalled();
  });
});
