import { Card, CardContent } from "@/components/ui/card";

export function MetricCard({ label, value, detail }: { label: string; value: string | number; detail?: string }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <p className="text-sm text-muted-foreground">{label}</p>
        <strong className="mt-2 block text-3xl font-semibold tracking-tight">{value}</strong>
        {detail ? <p className="mt-2 text-sm text-muted-foreground">{detail}</p> : null}
      </CardContent>
    </Card>
  );
}
