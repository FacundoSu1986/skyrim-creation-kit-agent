import { getDocumentBySlug } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ slug: string }> },
) {
  const { slug } = await context.params;
  const doc = await getDocumentBySlug(slug);
  if (!doc) {
    return Response.json({ error: "not_found" }, { status: 404 });
  }
  return Response.json(doc);
}
