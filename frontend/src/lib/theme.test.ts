import { afterEach, describe, expect, it, vi } from "vitest";
import { applyTheme, readTheme, saveTheme } from "./theme";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("tema", () => {
  it("sem nada salvo, o tema é escuro", () => {
    expect(readTheme()).toBe("dark");
  });

  it("valor salvo inválido cai no escuro", () => {
    localStorage.setItem("dm-theme", "roxo");
    expect(readTheme()).toBe("dark");
  });

  it("storage bloqueado cai no escuro", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    expect(readTheme()).toBe("dark");
  });

  it("salva e relê a escolha", () => {
    saveTheme("light");
    expect(readTheme()).toBe("light");
  });

  it("salvar com storage bloqueado não quebra", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    expect(() => saveTheme("light")).not.toThrow();
  });

  it("applyTheme('dark') põe a classe dark no html; 'light' tira", () => {
    applyTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    applyTheme("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("'system' segue a preferência do sistema", () => {
    vi.spyOn(window, "matchMedia").mockReturnValue({ matches: true } as MediaQueryList);
    applyTheme("system");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });
});
