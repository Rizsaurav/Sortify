import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import { DragDropCategory } from "../DragDropCategory";

describe("DragDropCategory Component", () => {
  const mockFile = { id: "file-1", name: "invoice.pdf", category: "General" };
  const mockCategories = [
    { id: 1, label: "Finance", color: "#3B82F6", user_created: true },
    { id: 2, label: "Reports", color: "#10B981" },
  ];

  const mockOnChange = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => vi.clearAllMocks());

  it("renders file information and category list correctly", () => {
    render(
      <DragDropCategory
        file={mockFile}
        categories={mockCategories}
        onCategoryChange={mockOnChange}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getAllByText("invoice.pdf").length).toBeGreaterThan(0);
    expect(screen.getByText("Finance")).toBeInTheDocument();
    expect(screen.getByText("Reports")).toBeInTheDocument();
  });

  it("invokes onCategoryChange when a category is clicked", () => {
    render(
      <DragDropCategory
        file={mockFile}
        categories={mockCategories}
        onCategoryChange={mockOnChange}
        onCancel={mockOnCancel}
      />
    );

    fireEvent.click(screen.getByText("Reports"));
    expect(mockOnChange).toHaveBeenCalledWith("file-1", 2, "Reports");
  });

  it("invokes onCategoryChange when a file is dropped into a category", () => {
    render(
      <DragDropCategory
        file={mockFile}
        categories={mockCategories}
        onCategoryChange={mockOnChange}
        onCancel={mockOnCancel}
      />
    );

    const fileCard = screen.getAllByText("invoice.pdf")[1].closest("div")!;
    const dropZone = screen.getByText("Finance").closest("div")!;
    const dataTransfer = { setData: vi.fn(), getData: vi.fn(() => "file-1"), dropEffect: "" };

    fireEvent.dragStart(fileCard, { dataTransfer });
    fireEvent.dragOver(dropZone, { dataTransfer });
    fireEvent.drop(dropZone, { dataTransfer });

    expect(mockOnChange).toHaveBeenCalledWith("file-1", 1, "Finance");
  });

  it("renders the category area during drag-over interaction", () => {
    render(
      <DragDropCategory
        file={mockFile}
        categories={mockCategories}
        onCategoryChange={mockOnChange}
        onCancel={mockOnCancel}
      />
    );

    const dropZone = screen.getByText("Finance").closest("div")!;
    const dataTransfer = { setData: vi.fn(), getData: vi.fn(() => "file-1"), dropEffect: "" };
    fireEvent.dragOver(dropZone, { dataTransfer });

    expect(dropZone).toBeInTheDocument();
  });

  it("invokes onCancel when the cancel button is clicked", () => {
    render(
      <DragDropCategory
        file={mockFile}
        categories={mockCategories}
        onCategoryChange={mockOnChange}
        onCancel={mockOnCancel}
      />
    );

    fireEvent.click(screen.getByText("Cancel"));
    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });
});
