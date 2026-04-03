import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TagList from "../components/TagList";

describe("TagList", () => {
  it("renders no tags when empty", () => {
    const { container } = render(<TagList tags={[]} />);
    expect(container.querySelectorAll("span")).toHaveLength(0);
  });

  it("renders all tags with # prefix", () => {
    render(<TagList tags={["nature", "landscape", "travel"]} />);
    expect(screen.getByText("#nature")).toBeInTheDocument();
    expect(screen.getByText("#landscape")).toBeInTheDocument();
    expect(screen.getByText("#travel")).toBeInTheDocument();
  });

  it("shows +N more when maxVisible is set", () => {
    render(<TagList tags={["a", "b", "c", "d", "e"]} maxVisible={3} />);
    expect(screen.getByText("+2 more")).toBeInTheDocument();
  });

  it("shows no overflow indicator when all tags fit", () => {
    render(<TagList tags={["a", "b"]} maxVisible={5} />);
    expect(screen.queryByText(/more/)).not.toBeInTheDocument();
  });

  it("renders input field in editable mode", () => {
    render(<TagList tags={[]} editable />);
    expect(screen.getByPlaceholderText("Add tag...")).toBeInTheDocument();
  });

  it("does not render input in read-only mode", () => {
    render(<TagList tags={["a"]} />);
    expect(screen.queryByPlaceholderText("Add tag...")).not.toBeInTheDocument();
  });

  it("renders remove buttons in editable mode", () => {
    render(<TagList tags={["a", "b"]} editable />);
    expect(screen.getAllByRole("button")).toHaveLength(2);
  });

  it("calls onChange when a tag is removed", async () => {
    const onChange = vi.fn();
    render(<TagList tags={["x", "y"]} editable onChange={onChange} />);
    const buttons = screen.getAllByRole("button");
    await userEvent.click(buttons[0]);
    expect(onChange).toHaveBeenCalledWith(["y"]);
  });

  it("adds a tag on Enter key press", async () => {
    const onChange = vi.fn();
    render(<TagList tags={[]} editable onChange={onChange} />);
    const input = screen.getByPlaceholderText("Add tag...");
    await userEvent.type(input, "newtag{Enter}");
    expect(onChange).toHaveBeenCalledWith(["newtag"]);
  });

  it("does not add duplicate tags", async () => {
    const onChange = vi.fn();
    render(<TagList tags={["existing"]} editable onChange={onChange} />);
    const input = screen.getByPlaceholderText("Add tag...");
    await userEvent.type(input, "existing{Enter}");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("strips trailing comma when adding via comma key", async () => {
    const onChange = vi.fn();
    render(<TagList tags={[]} editable onChange={onChange} />);
    const input = screen.getByPlaceholderText("Add tag...");
    await userEvent.type(input, "comma,");
    expect(onChange).toHaveBeenCalledWith(["comma"]);
  });
});
