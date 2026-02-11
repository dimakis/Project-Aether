import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { YamlEditor } from "../yaml-editor";

// Mock the CodeBlock used by YamlViewer so we can inspect its output
vi.mock("../code-block", () => ({
  CodeBlock: ({ code }: { code: string }) => (
    <pre data-testid="code-block">{code}</pre>
  ),
}));

const SAMPLE_YAML = `trigger:
  - platform: sun
    event: sunset
action:
  - service: light.turn_on
    entity_id: light.living_room`;

describe("YamlEditor", () => {
  describe("view mode", () => {
    it("renders YAML in read-only mode by default", () => {
      render(
        <YamlEditor
          originalYaml={SAMPLE_YAML}
          isEditing={false}
          onSubmitEdit={vi.fn()}
          onCancelEdit={vi.fn()}
        />,
      );
      expect(screen.getByTestId("code-block")).toHaveTextContent(/trigger/);
      expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    });

    it("does not show action buttons in view mode", () => {
      render(
        <YamlEditor
          originalYaml={SAMPLE_YAML}
          isEditing={false}
          onSubmitEdit={vi.fn()}
          onCancelEdit={vi.fn()}
        />,
      );
      expect(
        screen.queryByRole("button", { name: /cancel/i }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /send to architect/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("edit mode", () => {
    it("shows a textarea with the original YAML", () => {
      render(
        <YamlEditor
          originalYaml={SAMPLE_YAML}
          isEditing={true}
          onSubmitEdit={vi.fn()}
          onCancelEdit={vi.fn()}
        />,
      );
      const textarea = screen.getByRole("textbox");
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveValue(SAMPLE_YAML);
    });

    it("shows Cancel and Send to Architect buttons", () => {
      render(
        <YamlEditor
          originalYaml={SAMPLE_YAML}
          isEditing={true}
          onSubmitEdit={vi.fn()}
          onCancelEdit={vi.fn()}
        />,
      );
      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /send to architect/i }),
      ).toBeInTheDocument();
    });

    it("calls onCancelEdit when Cancel is clicked", async () => {
      const onCancel = vi.fn();
      const user = userEvent.setup();
      render(
        <YamlEditor
          originalYaml={SAMPLE_YAML}
          isEditing={true}
          onSubmitEdit={vi.fn()}
          onCancelEdit={onCancel}
        />,
      );
      await user.click(screen.getByRole("button", { name: /cancel/i }));
      expect(onCancel).toHaveBeenCalledOnce();
    });

    it("calls onSubmitEdit with edited YAML when submitted", async () => {
      const onSubmit = vi.fn();
      const user = userEvent.setup();
      render(
        <YamlEditor
          originalYaml={SAMPLE_YAML}
          isEditing={true}
          onSubmitEdit={onSubmit}
          onCancelEdit={vi.fn()}
        />,
      );
      const textarea = screen.getByRole("textbox");
      // Use fireEvent to avoid userEvent special character issues with []
      fireEvent.change(textarea, { target: { value: "trigger: []" } });
      await user.click(
        screen.getByRole("button", { name: /send to architect/i }),
      );
      expect(onSubmit).toHaveBeenCalledWith("trigger: []");
    });

    it("shows a valid indicator for correct YAML", () => {
      render(
        <YamlEditor
          originalYaml={SAMPLE_YAML}
          isEditing={true}
          onSubmitEdit={vi.fn()}
          onCancelEdit={vi.fn()}
        />,
      );
      expect(screen.getByText(/valid yaml/i)).toBeInTheDocument();
    });

    it("shows an error indicator for invalid YAML", () => {
      render(
        <YamlEditor
          originalYaml={SAMPLE_YAML}
          isEditing={true}
          onSubmitEdit={vi.fn()}
          onCancelEdit={vi.fn()}
        />,
      );
      const textarea = screen.getByRole("textbox");
      fireEvent.change(textarea, { target: { value: "invalid: [unclosed" } });
      expect(screen.getByText(/invalid yaml/i)).toBeInTheDocument();
    });

    it("disables submit button when YAML is invalid", () => {
      render(
        <YamlEditor
          originalYaml={SAMPLE_YAML}
          isEditing={true}
          onSubmitEdit={vi.fn()}
          onCancelEdit={vi.fn()}
        />,
      );
      const textarea = screen.getByRole("textbox");
      fireEvent.change(textarea, { target: { value: "invalid: [unclosed" } });
      expect(
        screen.getByRole("button", { name: /send to architect/i }),
      ).toBeDisabled();
    });

    it("disables submit button when content is unchanged", () => {
      render(
        <YamlEditor
          originalYaml={SAMPLE_YAML}
          isEditing={true}
          onSubmitEdit={vi.fn()}
          onCancelEdit={vi.fn()}
        />,
      );
      expect(
        screen.getByRole("button", { name: /send to architect/i }),
      ).toBeDisabled();
    });
  });
});
