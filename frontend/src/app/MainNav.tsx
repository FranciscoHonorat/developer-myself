import { CircleUser, type LucideIcon, NotebookPen, Route, Sun, TrendingUp } from "lucide-react";
import { NavLink } from "react-router";
import { cn } from "@/lib/utils";
import { Brand } from "./Brand";

export interface Section {
  to: string;
  label: string;
  icon: LucideIcon;
}

export const SECTIONS: Section[] = [
  { to: "/hoje", label: "Hoje", icon: Sun },
  { to: "/trilha", label: "Trilha", icon: Route },
  { to: "/caderno", label: "Caderno", icon: NotebookPen },
  { to: "/progresso", label: "Progresso", icon: TrendingUp },
];

const linkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex flex-1 flex-col items-center justify-center gap-1 rounded-md px-2 py-1.5 text-[11px] font-medium transition-colors",
    "sm:flex-none sm:size-10 sm:p-0 lg:size-auto lg:flex-row lg:justify-start lg:gap-3 lg:px-3 lg:py-2 lg:text-sm",
    "outline-none focus-visible:ring-2 focus-visible:ring-ring",
    isActive
      ? "text-primary sm:bg-accent sm:text-accent-foreground"
      : "text-muted-foreground hover:bg-muted hover:text-foreground",
  );

function NavItem({ to, label, icon: Icon, className }: Section & { className?: string }) {
  return (
    <NavLink to={to} title={label} className={(st) => cn(linkClass(st), className)}>
      <Icon aria-hidden className="size-5 lg:size-4" />
      <span className="sm:sr-only lg:not-sr-only">{label}</span>
    </NavLink>
  );
}

/**
 * Uma única navegação "Seções" que muda de forma: barra fixa embaixo no celular,
 * coluna só de ícones no tablet e menu lateral completo no desktop.
 */
export function MainNav() {
  return (
    <nav
      aria-label="Seções"
      className={cn(
        "fixed inset-x-0 bottom-0 z-40 flex h-16 items-stretch gap-1 border-t bg-card/95 px-2 pb-[env(safe-area-inset-bottom)] backdrop-blur",
        "sm:sticky sm:top-0 sm:h-dvh sm:w-16 sm:flex-col sm:items-center sm:gap-2 sm:border-t-0 sm:border-r sm:px-0 sm:py-4",
        "lg:w-60 lg:items-stretch lg:px-3",
      )}
    >
      <div className="hidden sm:mb-4 sm:flex sm:justify-center lg:justify-start lg:px-3">
        <Brand className="hidden lg:inline" />
        <span aria-hidden className="font-mono text-sm font-bold text-primary lg:hidden">
          &gt;_
        </span>
      </div>
      {SECTIONS.map((s) => (
        <NavItem key={s.to} {...s} />
      ))}
      <NavItem to="/conta" label="Conta" icon={CircleUser} className="hidden sm:flex sm:mt-auto" />
    </nav>
  );
}
