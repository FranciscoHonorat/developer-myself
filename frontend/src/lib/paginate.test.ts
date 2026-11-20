import { describe, expect, it } from "vitest";
import { pageContaining, paginate } from "./paginate";

const items = Array.from({ length: 13 }, (_, i) => i + 1);

describe("paginate", () => {
  it("corta a página pedida e conta o total de páginas", () => {
    expect(paginate(items, 1, 6)).toEqual({ items: [1, 2, 3, 4, 5, 6], page: 1, totalPages: 3 });
    expect(paginate(items, 3, 6)).toEqual({ items: [13], page: 3, totalPages: 3 });
  });

  it("página fora do intervalo (URL antiga, item removido) cai na mais próxima", () => {
    expect(paginate(items, 9, 6).page).toBe(3);
    expect(paginate(items, 0, 6).page).toBe(1);
    expect(paginate(items, Number.NaN, 6).page).toBe(1);
  });

  it("lista vazia tem uma página vazia", () => {
    expect(paginate([], 1, 6)).toEqual({ items: [], page: 1, totalPages: 1 });
  });
});

describe("pageContaining", () => {
  it("diz em que página está um item", () => {
    expect(pageContaining(items, (n) => n === 7, 6)).toBe(2);
    expect(pageContaining(items, (n) => n === 99, 6)).toBeNull();
  });
});
