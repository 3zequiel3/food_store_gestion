export function ProductCardSkeleton() {
  return (
    <div className="flex flex-col rounded-xl bg-glass backdrop-blur-xl border border-glass-border overflow-hidden">
      <div className="aspect-square w-full bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
      <div className="flex flex-col gap-3 p-4">
        <div className="h-4 w-3/4 rounded-md bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
        <div className="h-4 w-1/3 rounded-md bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
        <div className="h-9 w-full rounded-lg bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%] mt-1" />
      </div>
    </div>
  );
}
