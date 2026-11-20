import { createBrowserRouter, createMemoryRouter, Navigate, type RouteObject } from "react-router";
import { AuthPage } from "@/pages/AuthPage";
import { AppShell } from "./AppShell";
import { RequireAuth } from "./RequireAuth";

// Cada seção é um chunk próprio: o primeiro carregamento só baixa a casca e a seção aberta.
const page = (load: () => Promise<{ Component: () => React.JSX.Element }>) => ({ lazy: load });

export const routes: RouteObject[] = [
  { path: "/entrar", element: <AuthPage mode="login" /> },
  { path: "/cadastro", element: <AuthPage mode="register" /> },
  {
    path: "/",
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/hoje" replace /> },
      {
        path: "hoje",
        ...page(() => import("@/pages/TodayPage").then((m) => ({ Component: m.TodayPage }))),
      },
      {
        path: "trilha",
        ...page(() => import("@/pages/TrailPage").then((m) => ({ Component: m.TrailPage }))),
      },
      {
        path: "caderno",
        ...page(() => import("@/pages/NotebookPage").then((m) => ({ Component: m.NotebookPage }))),
      },
      {
        path: "caderno/:contentId",
        ...page(() => import("@/pages/NotebookPage").then((m) => ({ Component: m.NotebookPage }))),
      },
      {
        path: "progresso",
        ...page(() => import("@/pages/ProgressPage").then((m) => ({ Component: m.ProgressPage }))),
      },
      {
        path: "conta",
        ...page(() => import("@/pages/AccountPage").then((m) => ({ Component: m.AccountPage }))),
      },
      { path: "*", element: <Navigate to="/hoje" replace /> },
    ],
  },
];

/** Browser router no app; memory router nos testes (`initialEntries`). */
export function createAppRouter(opts: { initialEntries?: string[] } = {}) {
  return opts.initialEntries
    ? createMemoryRouter(routes, { initialEntries: opts.initialEntries })
    : createBrowserRouter(routes);
}
