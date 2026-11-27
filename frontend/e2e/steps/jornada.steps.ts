import { expect, type Page } from "@playwright/test";
import { createBdd } from "playwright-bdd";

const { Given, When, Then } = createBdd();

/** O resultado da sessão abre num diálogo modal: fecha antes de navegar. */
async function closeOutcome(page: Page) {
  const dialog = page.getByRole("dialog");
  if (await dialog.isVisible()) await dialog.getByRole("button", { name: "Continuar" }).click();
}

Given("que eu criei uma conta nova", async ({ page }) => {
  await page.goto("/cadastro");
  const id = crypto.randomUUID().slice(0, 8);
  await page.getByLabel("Username").fill(`e2e-${id}`);
  await page.getByLabel("E-mail").fill(`e2e-${id}@exemplo.com`);
  await page.getByLabel("Senha").fill("senha-forte-e2e-123");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await expect(page.getByRole("heading", { name: "Adicione seu primeiro conteúdo" })).toBeVisible();
});

When("eu adiciono o conteúdo {string}", async ({ page }, title: string) => {
  await page
    .getByRole("navigation", { name: "Seções" })
    .getByRole("link", { name: "Trilha" })
    .click();
  await page.getByRole("button", { name: "Adicionar conteúdo" }).click();
  const dialog = page.getByRole("dialog", { name: "Adicionar conteúdo" });
  await dialog.getByLabel("Título").fill(title);
  await dialog.getByRole("button", { name: "Adicionar" }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
});

When("eu inicio uma sessão de estudo em {string}", async ({ page }, title: string) => {
  await page
    .getByRole("article", { name: title })
    .getByRole("button", { name: /Estudar/ })
    .click();
  await expect(page.getByRole("heading", { name: `Estudo: ${title}` })).toBeVisible();
  await expect(page.getByRole("timer")).toBeVisible();
});

When("eu finalizo a sessão com as minhas anotações", async ({ page }) => {
  await page.getByLabel("O que estudei").fill("Funções pequenas e nomes que revelam a intenção");
  await page.getByLabel("O que entendi").fill("Uma função deve fazer uma única coisa");
  await page.getByLabel("O que preciso revisar").fill("Separação entre comando e consulta");
  await page.getByRole("button", { name: "Finalizar sessão" }).click();
});

Then("vejo que a sessão não valeu ponto porque foi curta", async ({ page }) => {
  await expect(page.getByText("Sessão sem ponto.")).toBeVisible();
  await expect(page.getByText(/pelo menos 25 minutos/)).toBeVisible();
});

Then("a sessão aparece no meu histórico", async ({ page }) => {
  await closeOutcome(page);
  await page
    .getByRole("navigation", { name: "Seções" })
    .getByRole("link", { name: "Progresso" })
    .click();
  await page.getByRole("tab", { name: "Histórico" }).click();
  await expect(page.getByText("Separação entre comando e consulta")).toBeVisible();
});

Then(
  "{string} aparece bloqueado esperando {string}",
  async ({ page }, title: string, current: string) => {
    const card = page.getByRole("article", { name: title });
    await expect(card.getByText(`conclua ${current} ou chegue a Intermediário`)).toBeVisible();
    await expect(card.getByRole("button", { name: /Estudar|Revisar/ })).toHaveCount(0);
  },
);

When("eu escrevo no caderno {string}", async ({ page }, text: string) => {
  await page.getByLabel(/Caderno de/).fill(text);
  await expect(page.getByRole("status").filter({ hasText: /Salvo/ })).toBeVisible();
});

When("eu abro {string} na aba Caderno", async ({ page }, title: string) => {
  await expect(page.getByRole("dialog")).toBeVisible();
  await closeOutcome(page);
  await page
    .getByRole("navigation", { name: "Seções" })
    .getByRole("link", { name: "Caderno" })
    .click();
  await page
    .getByRole("navigation", { name: "Matérias" })
    .getByRole("link", { name: new RegExp(`^${title}`) })
    .click();
});

Then("vejo {string} no caderno", async ({ page }, text: string) => {
  await expect(page.getByLabel(/Caderno de/)).toHaveValue(text);
});

Then(
  "o botão {string} fica visível acima da barra de navegação",
  async ({ page }, name: string) => {
    const button = page.getByRole("button", { name });
    await button.scrollIntoViewIfNeeded();
    await expect(button).toBeInViewport();
    const btn = await button.boundingBox();
    const nav = await page.getByRole("navigation", { name: "Seções" }).boundingBox();
    expect(btn && nav && btn.y + btn.height <= nav.y).toBe(true);
  },
);

const SECTIONS = ["/hoje", "/trilha", "/caderno", "/progresso", "/conta"];

Then("o fim de cada seção fica visível acima da barra de navegação", async ({ page }) => {
  for (const path of SECTIONS) {
    await page.goto(path);
    await page.getByRole("heading", { level: 1 }).first().waitFor();
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    const gap = await page.evaluate(() => {
      const main = document.querySelector("main");
      const last = main?.lastElementChild;
      const nav = document.querySelector('nav[aria-label="Seções"]');
      if (!last || !nav) return Number.NaN;
      return nav.getBoundingClientRect().top - last.getBoundingClientRect().bottom;
    });
    expect(gap, `fim de ${path} escondido atrás da barra`).toBeGreaterThanOrEqual(0);
  }
});

Then("a página não rola na horizontal", async ({ page }) => {
  for (const path of SECTIONS) {
    await page.goto(path);
    await page.getByRole("heading", { level: 1 }).first().waitFor();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow, `rolagem horizontal em ${path}`).toBeLessThanOrEqual(0);
  }
});

// ---------------------------------------------------------------- aquecimento
When("eu deixo para o eu do futuro a pergunta {string}", async ({ page }, text: string) => {
  await page.getByText("💭 Deixar uma pergunta para o seu eu do futuro (opcional)").click();
  await page.getByLabel("Pergunta", { exact: true }).fill(text);
});

When("eu volto para a tela Hoje", async ({ page }) => {
  await expect(page.getByRole("dialog")).toBeVisible();
  await closeOutcome(page);
  await page
    .getByRole("navigation", { name: "Seções" })
    .getByRole("link", { name: "Hoje" })
    .click();
});

When("eu começo o aquecimento", async ({ page }) => {
  await expect(page.getByText("🔥 Aquecimento · 2 perguntas · ~2 min")).toBeVisible();
  await page.getByRole("button", { name: "Começar" }).click();
});

Then("a 1ª pergunta do aquecimento é {string}", async ({ page }, text: string) => {
  const first = page.getByRole("region", { name: "🔥 Aquecimento" }).getByRole("listitem").first();
  await expect(first).toContainText(text);
});

When("eu corrijo e concluo o aquecimento", async ({ page }) => {
  const panel = page.getByRole("region", { name: "🔥 Aquecimento" });
  await panel.getByRole("button", { name: "Conferir respostas" }).click();
  for (const group of await panel.getByRole("radiogroup", { name: /Correção/ }).all()) {
    await group.getByText("Acertei").click();
  }
  await panel.getByRole("button", { name: "Concluir aquecimento" }).click();
});

Then("vejo que o aquecimento foi feito, sem repetir o estudo de hoje", async ({ page }) => {
  // "Clean Code" já foi estudado hoje: o próximo passo da tela Hoje não o repete.
  await expect(page.getByText("✅ Aquecimento feito.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Iniciar sessão" })).toHaveCount(0);
});

When("eu encerro por hoje", async ({ page }) => {
  await page.getByRole("button", { name: "Por hoje é só" }).click();
});

Then("a tela Hoje mostra que o aquecimento de hoje está feito", async ({ page }) => {
  await expect(page.getByText("✅ Aquecimento feito hoje")).toBeVisible();
});
