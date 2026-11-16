import { expect, it, describe, afterEach } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import "@testing-library/jest-dom/vitest";

expect.extend(toHaveNoViolations);

afterEach(cleanup);

describe("HomePage accessibility", () => {
  it("has no accessibility violations", async () => {
    const { HomePage } = await import(/* @vite-ignore */ "./HomePage");
    const { container } = render(<HomePage />);
    const results = await axe(container);

    expect(results).toHaveNoViolations();
  });
});
