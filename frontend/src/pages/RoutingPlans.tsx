import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listRoutingPlans,
  getRoutingPlanSummary,
  approveRoutingPlanItems,
  rejectRoutingPlanItems,
  applyRoutingPlan,
  startRoutingClassify,
} from "../services/api";
import type { RoutingPlanSummary, RoutingPlanGroupItem } from "../types";
import { CheckCircle2, AlertTriangle, Trash2, XCircle, Clock, Play, type LucideIcon } from "lucide-react";

const GROUP_DEFS: {
  key: keyof RoutingPlanSummary["groups"];
  label: string;
  color: string;
  icon: LucideIcon;
}[] = [
  { key: "auto_applied", label: "Auto-applied", color: "#22c55e", icon: CheckCircle2 },
  { key: "ready_to_approve", label: "Ready to approve", color: "#38bdf8", icon: CheckCircle2 },
  { key: "needs_review", label: "Needs review", color: "#f59e0b", icon: AlertTriangle },
  { key: "trash_candidates", label: "Trash candidates", color: "#ef4444", icon: Trash2 },
  { key: "rejected", label: "Rejected by rules", color: "#64748b", icon: XCircle },
  { key: "failed", label: "Failed", color: "#ef4444", icon: XCircle },
];

export default function RoutingPlans() {
  const qc = useQueryClient();
  const { data: plans = [] } = useQuery({ queryKey: ["routing-plans"], queryFn: () => listRoutingPlans() });
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);

  const { data: summary } = useQuery<RoutingPlanSummary>({
    queryKey: ["routing-plan-summary", selectedPlanId],
    queryFn: () => getRoutingPlanSummary(selectedPlanId!),
    enabled: !!selectedPlanId,
    refetchInterval: 5000,
  });

  const classifyMut = useMutation({
    mutationFn: () => startRoutingClassify({}),
    onSuccess: (r) => {
      setSelectedPlanId(r.plan_id);
      qc.invalidateQueries({ queryKey: ["routing-plans"] });
    },
  });

  const approveGroup = useMutation({
    mutationFn: (g: { planId: string; bucketId?: string | null; itemIds?: string[] }) =>
      approveRoutingPlanItems(g.planId, { bucket_id: g.bucketId ?? undefined, item_ids: g.itemIds }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["routing-plan-summary", selectedPlanId] });
    },
  });

  const rejectGroup = useMutation({
    mutationFn: (g: { planId: string; bucketId?: string | null; itemIds?: string[] }) =>
      rejectRoutingPlanItems(g.planId, { bucket_id: g.bucketId ?? undefined, item_ids: g.itemIds }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["routing-plan-summary", selectedPlanId] });
    },
  });

  const applyMut = useMutation({
    mutationFn: () => applyRoutingPlan(selectedPlanId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["routing-plan-summary", selectedPlanId] });
      qc.invalidateQueries({ queryKey: ["routing-plans"] });
    },
  });

  return (
    <div style={{ padding: "32px 40px", maxWidth: 1400 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Routing plans</h1>
          <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
            Review and apply batches of AI routing decisions.
          </p>
        </div>
        <button
          onClick={() => classifyMut.mutate()}
          disabled={classifyMut.isPending}
          style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "8px 16px", borderRadius: 8, border: "none",
            background: "#1e40af", color: "white", fontSize: 13, fontWeight: 600,
            cursor: classifyMut.isPending ? "wait" : "pointer",
          }}
        >
          <Play size={13} /> Run new plan
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 24 }}>
        <div style={{
          background: "#0f172a", border: "1px solid #1e293b",
          borderRadius: 12, padding: 16,
        }}>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 10 }}>
            Recent plans
          </div>
          {plans.length === 0 && (
            <div style={{ color: "#475569", fontSize: 13 }}>No plans yet. Run a routing job first.</div>
          )}
          {plans.map((p) => (
            <div
              key={p.id}
              onClick={() => setSelectedPlanId(p.id)}
              style={{
                padding: "10px 12px", borderRadius: 8, marginBottom: 6,
                background: selectedPlanId === p.id ? "rgba(59,130,246,0.12)" : "#1e293b",
                border: "1px solid #1e293b",
                cursor: "pointer",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Clock size={12} color="#64748b" />
                <span style={{ fontSize: 12, color: "#e2e8f0" }}>
                  {new Date(p.created_at).toLocaleString()}
                </span>
              </div>
              <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
                {p.status} · {p.item_count} item{p.item_count === 1 ? "" : "s"}
              </div>
            </div>
          ))}
        </div>

        <div>
          {!selectedPlanId && (
            <div style={{
              padding: 32, textAlign: "center",
              background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12,
              color: "#64748b",
            }}>
              Select a plan from the list, or run a new one.
            </div>
          )}
          {selectedPlanId && summary && (
            <div>
              <div style={{
                background: "#0f172a", border: "1px solid #1e293b",
                borderRadius: 12, padding: 16, marginBottom: 16,
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}>
                <div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>Plan total</div>
                  <div style={{ fontSize: 20, color: "#f1f5f9", fontWeight: 700 }}>
                    {summary.total} item{summary.total === 1 ? "" : "s"}
                  </div>
                </div>
                <button
                  onClick={() => applyMut.mutate()}
                  disabled={applyMut.isPending}
                  style={{
                    padding: "8px 16px", borderRadius: 8, border: "none",
                    background: "#22c55e", color: "white", fontSize: 13, fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Apply approved items
                </button>
              </div>

              {GROUP_DEFS.map(({ key, label, color, icon: Icon }) => {
                const items = (summary.groups[key] ?? []) as RoutingPlanGroupItem[];
                if (items.length === 0) return null;
                return (
                  <div key={key} style={{
                    background: "#0f172a", border: "1px solid #1e293b",
                    borderRadius: 12, padding: 16, marginBottom: 12,
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                      <Icon size={16} color={color} />
                      <h3 style={{ fontSize: 14, fontWeight: 700, color, margin: 0 }}>{label}</h3>
                      <span style={{ color: "#64748b", fontSize: 12, marginLeft: 4 }}>
                        ({items.reduce((s, g) => s + g.count, 0)})
                      </span>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {items.map((g) => (
                        <div key={g.path} style={{
                          display: "flex", alignItems: "center", gap: 8,
                          padding: "8px 12px", borderRadius: 8,
                          background: "#1e293b", border: "1px solid #1e293b",
                        }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>{g.path}</div>
                            <div style={{ color: "#64748b", fontSize: 11 }}>{g.count} photos</div>
                          </div>
                          {(key === "ready_to_approve" || key === "needs_review" || key === "trash_candidates") && (
                            <>
                              <button
                                onClick={() => approveGroup.mutate({
                                  planId: selectedPlanId,
                                  bucketId: g.bucket_id,
                                  itemIds: g.item_ids,
                                })}
                                style={{
                                  padding: "5px 10px", borderRadius: 6,
                                  border: "none", background: "#1e40af",
                                  color: "white", fontSize: 11, fontWeight: 600, cursor: "pointer",
                                }}
                              >
                                Approve
                              </button>
                              <button
                                onClick={() => rejectGroup.mutate({
                                  planId: selectedPlanId,
                                  bucketId: g.bucket_id,
                                  itemIds: g.item_ids,
                                })}
                                style={{
                                  padding: "5px 10px", borderRadius: 6,
                                  border: "1px solid #334155", background: "transparent",
                                  color: "#ef4444", fontSize: 11, fontWeight: 600, cursor: "pointer",
                                }}
                              >
                                Reject
                              </button>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
