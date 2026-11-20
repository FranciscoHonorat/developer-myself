import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { renderWithClient } from "@/test/render";
import { ThemeSelect } from "./ThemeSelect";

afterEach(() => {
  localStorage.clear();
  document.documentElement.classList.add("dark");
});

describe("ThemeSelect", () => {
  it("troca e salva o tema", async () => {
    document.documentElement.classList.add("dark");
    renderWithClient(<ThemeSelect />);
    const group = screen.getByRole("radiogroup", { name: "Tema" });
    expect(screen.getByRole("radio", { name: "Escuro" })).toBeChecked();
    await userEvent.setup().click(screen.getByRole("radio", { name: "Claro" }));
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(localStorage.getItem("dm-theme")).toBe("light");
    expect(group).toBeInTheDocument();
  });
});
