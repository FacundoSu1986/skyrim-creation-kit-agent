import { STATUS_LABELS, statusClass } from "@/lib/status";

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`badge ${statusClass(status)}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}
