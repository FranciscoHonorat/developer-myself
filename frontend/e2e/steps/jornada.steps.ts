import { expect } from "@playwright/test";
import { createBdd } from "playwright-bdd";

const { Given, When, Then } = createBdd();

Given("que eu criei uma conta nova", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Não tem conta? Cadastre-se" }).click();
  await page.getByLabel("E-mail").fill(`e2e-${crypto.randomUUID()}@exemplo.com`);
  await page.getByLabel("Senha").fill("senha-forte-e2e-123");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await expect(page.getByRole("heading", { name: "Em andamento" })).toBeVisible();
});

When("eu adiciono o conteúdo {string}", async ({ page }, title: string) => {
  await page.getByLabel("Novo conteúdo").fill(title);
  await page.getByRole("button", { name: "Adicionar" }).click();
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
  await page.getByRole("button", { name: "Histórico" }).click();
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
