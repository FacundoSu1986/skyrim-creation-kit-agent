import { getVerdict } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET() {
  const verdict = await getVerdict();
  return Response.json(verdict);
}
