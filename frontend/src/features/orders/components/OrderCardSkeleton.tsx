export function OrderCardSkeleton() {
  return (
    <div className="rounded-xl bg-glass backdrop-blur-xl border border-glass-border p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1.5">
          <div className="h-4 w-24 rounded-md bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
          <div className="h-3 w-32 rounded-md bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
        </div>
        <div className="h-5 w-20 rounded-full bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
      </div>
      <div className="flex items-center justify-between">
        <div className="h-4 w-16 rounded-md bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
        <div className="h-4 w-12 rounded-md bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
      </div>
    </div>
  );
}
