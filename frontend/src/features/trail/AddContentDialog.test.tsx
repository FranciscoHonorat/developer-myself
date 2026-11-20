import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { jsonResponse, makeContent, renderWithClient } from "@/test/render";
import { AddContentForm } from "./AddContentDialog";

afterEach(() => vi.restoreAllMocks());

/** Some quando `register` é chamado — como o guia some quando a trilha deixa de estar vazia. */
function HidingHost(props: { onAdded: () => void; register: (hide: () => void) => void }) {
  const [shown, setShown] = useState(true);
  props.register(() => setShown(false));
  return shown ? <AddContentForm onAdded={props.onAdded} /> : null;
}

describe("AddContentForm", () => {
  it("avisa que adicionou mesmo se o formulário some antes da resposta chegar", async () => {
    let hide = () => {};
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
      hide();
      await new Promise((r) => setTimeout(r, 20));
      return jsonResponse(makeContent({ id: "c9", title: "Docker" }));
    });
    const onAdded = vi.fn();
    renderWithClient(
      <HidingHost
        onAdded={onAdded}
        register={(h) => {
          hide = h;
        }}
      />,
    );
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Título"), "Docker");
    await user.click(screen.getByRole("button", { name: "Adicionar" }));
    await waitFor(() => expect(onAdded).toHaveBeenCalled());
  });
});
