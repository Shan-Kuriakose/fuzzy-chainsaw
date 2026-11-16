import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

afterEach(cleanup);

async function renderHomePage() {
  const { HomePage } = await import(/* @vite-ignore */ "./HomePage");
  return render(<HomePage />);
}

describe("HomePage", () => {
  it("renders the placeholder home page with a real level-1 heading", async () => {
    renderHomePage();

    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading).toBeInTheDocument();
    expect(heading).not.toBeEmptyDOMElement();
  });

  it("renders without console errors", async () => {
    const consoleErrors = vi.spyOn(console, "error");

    await renderHomePage();

    expect(consoleErrors).not.toHaveBeenCalled();
  });
});
