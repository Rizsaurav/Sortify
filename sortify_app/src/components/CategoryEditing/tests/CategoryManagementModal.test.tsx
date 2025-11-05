import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import "@testing-library/jest-dom";
import { CategoryManagementModal } from "../CategoryManagementModal";

describe("CategoryManagementModal Component", () => {
  const mockCategories = [
    { id: 1, label: "Finance", color: "#3B82F6", user_created: true },
    { id: 2, label: "Reports", color: "#10B981" },
  ];

  const mockHandlers = {
    onClose: vi.fn(),
    onCreateCategory: vi.fn(),
    onEditCategory: vi.fn(),
    onDeleteCategory: vi.fn(),
  };

  beforeEach(() => vi.clearAllMocks());

  const renderModal = (props = {}) =>
    render(
      <CategoryManagementModal
        isOpen={true}
        categories={mockCategories}
        {...mockHandlers}
        {...props}
      />
    );

  // ------------------------
  // CREATE TAB TESTS
  // ------------------------
  it("renders the create tab by default", () => {
    renderModal();

    // Both 'Create Category' (tab + submit)
    const createButtons = screen.getAllByText("Create Category");
    expect(createButtons.length).toBeGreaterThanOrEqual(2);

    // Placeholder ensures correct form is visible
    expect(
      screen.getByPlaceholderText("e.g., Invoice, Contract, Report")
    ).toBeInTheDocument();
  });
  it("creates a new category when valid inputs are entered", async () => {
    renderModal();
  
    // Find the name input directly by its placeholder
    const nameInput = screen.getByPlaceholderText("Enter category name") as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "New Category" } });
    expect(nameInput.value).toBe("New Category");
  
    // Pick a color button
    const colorButtons = screen
      .getAllByRole("button")
      .filter((btn) => btn.getAttribute("style")?.includes("background-color"));
    fireEvent.click(colorButtons[0]);
  
    // Find the bottom "Create Category" (submit) button by role and text
    const submitButton = screen.getAllByRole("button", { name: /Create Category/i }).find(
      (btn) => btn.className.includes("bg-blue-600")
    )!;
    fireEvent.click(submitButton);
  
    // Wait for async callback triggered by setTimeout in component
    await waitFor(() =>
      expect(mockHandlers.onCreateCategory).toHaveBeenCalledWith(
        "New Category",
        expect.stringMatching(/^#/),
        ""
      )
    );
  });
  


  it("switches to manage tab and renders existing categories", () => {
    renderModal();
    fireEvent.click(screen.getByText("Manage Categories"));
    expect(screen.getByText("Finance")).toBeInTheDocument();
    expect(screen.getByText("Reports")).toBeInTheDocument();
  });

  it("starts edit mode and saves changes", async () => {
    renderModal();
    fireEvent.click(screen.getByText("Manage Categories"));

    // Enter edit mode
    const editButton = screen.getAllByTitle("Edit category")[0];
    fireEvent.click(editButton);

    const input = screen.getByDisplayValue("Finance");
    fireEvent.change(input, { target: { value: "Finance Updated" } });

    // Find and click Save
    const saveButton = screen
      .getAllByRole("button")
      .find((btn) => /Save/i.test(btn.textContent || ""));
    fireEvent.click(saveButton!);

    // Wait for callback
    await waitFor(() =>
      expect(mockHandlers.onEditCategory).toHaveBeenCalledWith(
        1,
        "Finance Updated",
        expect.stringMatching(/^#/),
        expect.any(String)
      )
    );
  });

  it("deletes a category when confirmed", () => {
    vi.spyOn(window, "confirm").mockReturnValueOnce(true);
    renderModal();

    fireEvent.click(screen.getByText("Manage Categories"));
    const deleteButtons = screen.getAllByTitle("Delete category");
    fireEvent.click(deleteButtons[0]);

    expect(mockHandlers.onDeleteCategory).toHaveBeenCalledWith(1);
  });


  it("calls onClose when the close button is clicked", () => {
    renderModal();
    const closeButton = screen.getByText("Close");
    fireEvent.click(closeButton);
    expect(mockHandlers.onClose).toHaveBeenCalledTimes(1);
  });
});
