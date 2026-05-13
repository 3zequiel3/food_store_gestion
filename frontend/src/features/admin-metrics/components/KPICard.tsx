interface KPICardProps {
  label: string;
  value: string | number;
  isLoading?: boolean;
}

export function KPICard({ label, value, isLoading }: KPICardProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-5">
      <p className="text-sm text-muted-foreground mb-1">{label}</p>
      {isLoading ? (
        <div className="h-8 w-32 bg-muted rounded animate-pulse" />
      ) : (
        <p className="text-2xl font-bold text-foreground">{value}</p>
      )}
    </div>
  );
}
