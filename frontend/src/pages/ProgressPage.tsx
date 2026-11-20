import { useSearchParams } from "react-router";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Competencies } from "@/features/progress/Competencies";
import { SessionHistory } from "@/features/progress/SessionHistory";

type Aba = "competencias" | "historico";
const isAba = (v: string | null): v is Aba => v === "competencias" || v === "historico";

/** Progresso: Competências e Histórico em abas; a aba vive na URL (?aba=). */
export function ProgressPage() {
  const [params, setParams] = useSearchParams();
  const raw = params.get("aba");
  const aba: Aba = isAba(raw) ? raw : "competencias";
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold">Progresso</h1>
      <Tabs value={aba} onValueChange={(v) => setParams({ aba: v }, { replace: true })}>
        <TabsList>
          <TabsTrigger value="competencias">Competências</TabsTrigger>
          <TabsTrigger value="historico">Histórico</TabsTrigger>
        </TabsList>
        <TabsContent value="competencias" className="mt-4">
          <Competencies />
        </TabsContent>
        <TabsContent value="historico" className="mt-4">
          <SessionHistory />
        </TabsContent>
      </Tabs>
    </div>
  );
}
