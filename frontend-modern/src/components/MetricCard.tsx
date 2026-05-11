import { Card, CardContent } from "@/components/ui/card";

export function MetricCard({ label, value, detail }: { label: string; value: string | number; detail?: string }) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="pt-5">
        <p className="text-sm text-muted-foreground">{label}</p>
        <strong className="mt-2 block text-3xl font-semibold tracking-tight">{value}</strong>
        {detail ? <p className="mt-2 text-sm text-muted-foreground">{detail}</p> : null}
      </CardContent>
      <div className="h-1 bg-gradient-to-r from-primary via-slate-500 to-amber-500" />
    </Card>
  );
}
