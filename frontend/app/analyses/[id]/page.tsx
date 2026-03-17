import { AnalysisDashboard } from "@/components/analysis-dashboard";

export default async function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AnalysisDashboard analysisId={id} />;
}
