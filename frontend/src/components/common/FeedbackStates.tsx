import { AlertTriangle, ChevronLeft, ChevronRight, Inbox, RefreshCw } from "lucide-react";
import type { PaginationMeta } from "../../types/api";

export function LoadingSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-11 rounded-lg bg-[#151E2E] border border-[#263244]" />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[#263244] bg-[#151E2E]/60 px-6 py-10 text-center">
      <Inbox className="h-8 w-8 text-[#94A3B8]" />
      <h3 className="mt-3 text-sm font-semibold text-[#E2E8F0]">{title}</h3>
      <p className="mt-1 max-w-md text-xs text-[#94A3B8]">{description}</p>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-red-500/30 bg-red-500/10 px-6 py-8 text-center">
      <AlertTriangle className="h-8 w-8 text-red-400" />
      <h3 className="mt-3 text-sm font-semibold text-red-300">Failed to load data</h3>
      <p className="mt-1 max-w-lg text-xs text-red-200/80">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-red-400/40 bg-red-500/20 px-3 py-1.5 text-xs font-medium text-red-200 hover:bg-red-500/30"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Retry
        </button>
      )}
    </div>
  );
}

export function Pagination({
  pagination,
  onPageChange,
}: {
  pagination: PaginationMeta;
  onPageChange: (page: number) => void;
}) {
  const { page, total_pages, total, page_size } = pagination;
  const start = total === 0 ? 0 : (page - 1) * page_size + 1;
  const end = Math.min(total, page * page_size);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#263244] pt-3 text-xs text-[#94A3B8]">
      <span>
        Showing <strong className="text-[#E2E8F0]">{start.toLocaleString()}</strong>–
        <strong className="text-[#E2E8F0]">{end.toLocaleString()}</strong> of{" "}
        <strong className="text-[#E2E8F0]">{total.toLocaleString()}</strong>
      </span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="inline-flex items-center gap-1 rounded-lg border border-[#263244] bg-[#0B1120] px-2.5 py-1 text-[#E2E8F0] hover:border-[#38BDF8] disabled:opacity-40"
        >
          <ChevronLeft className="h-3.5 w-3.5" /> Prev
        </button>
        <span>
          Page <strong className="text-[#E2E8F0]">{page}</strong> / {total_pages}
        </span>
        <button
          type="button"
          disabled={page >= total_pages}
          onClick={() => onPageChange(page + 1)}
          className="inline-flex items-center gap-1 rounded-lg border border-[#263244] bg-[#0B1120] px-2.5 py-1 text-[#E2E8F0] hover:border-[#38BDF8] disabled:opacity-40"
        >
          Next <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  busy = false,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-md rounded-xl border border-[#263244] bg-[#151E2E] p-5 shadow-xl">
        <h3 className="text-base font-semibold text-[#E2E8F0]">{title}</h3>
        <p className="mt-2 text-xs leading-relaxed text-[#94A3B8]">{message}</p>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onCancel}
            className="rounded-lg border border-[#263244] bg-[#0B1120] px-3 py-1.5 text-xs font-medium text-[#E2E8F0] hover:border-[#94A3B8]"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onConfirm}
            className="rounded-lg bg-[#38BDF8] px-3 py-1.5 text-xs font-semibold text-[#0B1120] hover:bg-[#38BDF8]/90 disabled:opacity-50"
          >
            {busy ? "Submitting..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

