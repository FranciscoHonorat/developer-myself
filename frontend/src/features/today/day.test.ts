import { describe, expect, it } from "vitest";
import { makeBlock, makePlan, makeToday, makeTodayItem } from "../../test/fixtures";
import { makeContent } from "../../test/render";
import { dayItems, nextStep } from "./day";

const TODAY = "2026-11-20";
const review = makeTodayItem({ content_id: "r", title: "Redes", day: 11 });
const study = makeTodayItem({ content_id: "s", title: "Linux", day: 4 });
const contents = [
  makeContent({ id: "r", title: "Redes", status: "CONSOLIDATED" }),
  makeContent({ id: "s", title: "Linux" }),
];

describe("dayItems / nextStep", () => {
  it("revisões vêm antes dos estudos", () => {
    const items = dayItems(
      makeToday({ studies: [study], reviews: [review] }),
      makePlan({ contents }),
      TODAY,
    );
    expect(items.map((i) => [i.contentId, i.kind])).toEqual([
      ["r", "REVIEW"],
      ["s", "STUDY"],
    ]);
  });

  it("com revisão pendente, o próximo passo é a revisão mesmo com estudo listado", () => {
    const items = dayItems(
      makeToday({ studies: [study], reviews: [review] }),
      makePlan({ contents, needs_review_today: true }),
      TODAY,
    );
    expect(nextStep(items)?.contentId).toBe("r");
    expect(items.map((i) => i.state)).toEqual(["next", "later"]);
  });

  it("conteúdo com sessão hoje fica feito e o próximo passa ao seguinte", () => {
    const studied = [
      makeContent({ id: "s", title: "Linux", last_session_at: "2026-11-20T12:00:00Z" }),
      makeContent({ id: "t", title: "Go" }),
    ];
    const items = dayItems(
      makeToday({ studies: [study, makeTodayItem({ content_id: "t", title: "Go" })] }),
      makePlan({ contents: studied }),
      TODAY,
    );
    expect(items.map((i) => i.state)).toEqual(["done", "next"]);
    expect(nextStep(items)?.contentId).toBe("t");
  });

  it("revisão conta como feita quando reviewed_today", () => {
    const items = dayItems(
      makeToday({ studies: [study], reviews: [review] }),
      makePlan({ contents, reviewed_today: true }),
      TODAY,
    );
    expect(items.map((i) => i.state)).toEqual(["done", "next"]);
  });

  it("tudo feito → nextStep null", () => {
    const done = [makeContent({ id: "s", last_session_at: "2026-11-20T15:00:00Z" })];
    const items = dayItems(makeToday({ studies: [study] }), makePlan({ contents: done }), TODAY);
    expect(nextStep(items)).toBeNull();
  });

  it("last_session_at de ontem no fuso do plano não conta como hoje", () => {
    // 02:30 UTC do dia 20 = 23:30 do dia 19 em São Paulo
    const yesterday = [makeContent({ id: "s", last_session_at: "2026-11-20T02:30:00Z" })];
    const items = dayItems(
      makeToday({ studies: [study] }),
      makePlan({ contents: yesterday }),
      TODAY,
    );
    expect(items[0]?.state).toBe("next");
  });

  it("pomodoros e minutos vêm do bloco do mesmo conteúdo", () => {
    const items = dayItems(
      makeToday({
        studies: [study],
        blocks: [makeBlock({ content_id: "s", pomodoros: 3, minutes: 75 })],
      }),
      makePlan({ contents }),
      TODAY,
    );
    expect(items[0]).toMatchObject({ pomodoros: 3, minutes: 75, focus: "nomes e funções" });
  });
});
