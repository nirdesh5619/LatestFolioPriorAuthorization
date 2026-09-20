interface BadgeProps {
  text: string;
  className: string;
}

function Badge({ text, className }: BadgeProps) {
  return <span className={`badge ${className}`}>{text}</span>;
}

export function RiskBadge({ level }: { level: string | null }) {
  const normalized = (level ?? "unknown").toLowerCase();
  return <Badge text={normalized} className={`badge-${normalized}`} />;
}

export function ConfidenceBadge({ level }: { level: string }) {
  const normalized = level.toLowerCase();
  return <Badge text={normalized} className={`badge-${normalized}-confidence`} />;
}

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const className = normalized === "success" ? "badge-success" : "badge-error";
  return <Badge text={status} className={className} />;
}

const DETERMINATION_CLASSES: Record<string, string> = {
  approved: "badge-success",
  denied: "badge-error",
  pended: "badge-moderate",
};

export function DeterminationBadge({ determination }: { determination: string | null }) {
  const normalized = (determination ?? "pended").toLowerCase();
  return <Badge text={normalized} className={DETERMINATION_CLASSES[normalized] ?? "badge-unknown"} />;
}

const CRITERION_CLASSES: Record<string, string> = {
  MET: "badge-success",
  NOT_MET: "badge-error",
  UNKNOWN: "badge-moderate",
};

export function CriterionStatusBadge({ status }: { status: string }) {
  return <Badge text={status.replace("_", " ")} className={CRITERION_CLASSES[status] ?? "badge-unknown"} />;
}

export function ReviewStatusBadge({ status }: { status: string }) {
  const className = status === "reviewed" ? "badge-success" : "badge-moderate";
  return <Badge text={status.replace("_", " ")} className={className} />;
}

export function ReviewDecisionBadge({ decision }: { decision: string | null }) {
  if (!decision) return <Badge text="—" className="badge-unknown" />;
  const className = decision === "overridden" ? "badge-moderate" : "badge-success";
  return <Badge text={decision} className={className} />;
}
