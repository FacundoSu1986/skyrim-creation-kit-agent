import { getDashboard } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET() {
  const data = await getDashboard();
  return Response.json({
    verdict: data.verdict,
    statusCounts: data.statusCounts,
    documents: data.documents,
    gates: data.gates,
  });
}
