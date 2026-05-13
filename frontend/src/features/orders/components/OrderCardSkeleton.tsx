export function OrderCardSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-border bg-card p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1.5">
          <div className="h-4 w-24 rounded bg-muted" />
          <div className="h-3 w-32 rounded bg-muted" />
        </div>
        <div className="h-5 w-20 rounded-full bg-muted" />
      </div>
      <div className="flex items-center justify-between">
        <div className="h-4 w-16 rounded bg-muted" />
        <div className="h-4 w-12 rounded bg-muted" />
      </div>
    </div>
  );
}
