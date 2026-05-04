import React, { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getRoutingTree,
  createRoutingNode,
  updateRoutingNode,
  deleteRoutingNode,
  duplicateRoutingNode,
  startRoutingClassify,
} from "../services/api";
import type { RoutingNode } from "../types";
import RoutingLeafEditor from "../components/RoutingLeafEditor";
import {
  Plus,
  Trash2,
  Copy,
  ChevronRight,
  ChevronDown,
  Folder,
  FolderTree,
  Play,
} from "lucide-react";

const inputStyle: React.CSSProperties = {
  background: "#1e293b",
  border: "1px solid #334155",
  borderRadius: 8,
  color: "#f1f5f9",
  fontSize: 13,
  padding: "8px 12px",
  outline: "none",
};

interface NodeRowProps {
  node: RoutingNode;
  depth: number;
  expanded: Set<string>;
  toggle: (id: string) => void;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAddChild: (parentId: string) => void;
  onDuplicate: (id: string) => void;
  onDelete: (id: string) => void;
}

function NodeRow({
  node,
  depth,
  expanded,
  toggle,
  selectedId,
  onSelect,
  onAddChild,
  onDuplicate,
  onDelete,
}: NodeRowProps) {
  const hasChildren = (node.children?.length ?? 0) > 0;
  const isOpen = expanded.has(node.id);
  const isLeaf = node.is_leaf;
  const isSelected = selectedId === node.id;

  return (
    <>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          paddingLeft: depth * 16 + 4,
          padding: "6px 8px 6px 4px",
          borderRadius: 6,
          background: isSelected ? "rgba(59,130,246,0.12)" : "transparent",
          cursor: "pointer",
          opacity: node.enabled ? 1 : 0.55,
          marginBottom: 2,
        }}
        onClick={() => onSelect(node.id)}
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (hasChildren) toggle(node.id);
          }}
          style={{
            width: 20,
            background: "transparent",
            border: "none",
            color: "#64748b",
            cursor: hasChildren ? "pointer" : "default",
            display: "flex",
            alignItems: "center",
          }}
        >
          {hasChildren ? (
            isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />
          ) : (
            <span style={{ width: 14 }} />
          )}
        </button>
        {isLeaf ? <Folder size={14} color="#38bdf8" /> : <FolderTree size={14} color="#a78bfa" />}
        <div style={{ flex: 1, fontSize: 13, color: "#e2e8f0" }}>
          {node.name}
          <span style={{ fontSize: 11, color: "#64748b", marginLeft: 8 }}>
            {node.path}
          </span>
        </div>
        {node.destination_type !== "virtual" && (
          <span style={{
            fontSize: 10,
            color: "#38bdf8",
            background: "rgba(56,189,248,0.1)",
            padding: "1px 6px",
            borderRadius: 4,
          }}>
            {node.destination_type}
          </span>
        )}
        {node.auto_apply_enabled && (
          <span style={{
            fontSize: 10,
            color: "#22c55e",
            background: "rgba(34,197,94,0.1)",
            padding: "1px 6px",
            borderRadius: 4,
          }}>auto</span>
        )}
        <div style={{ display: "flex", gap: 4 }} onClick={(e) => e.stopPropagation()}>
          <button
            title="Add child"
            onClick={() => onAddChild(node.id)}
            style={{ padding: 4, background: "transparent", border: "none", color: "#64748b", cursor: "pointer" }}
          >
            <Plus size={13} />
          </button>
          <button
            title="Duplicate"
            onClick={() => onDuplicate(node.id)}
            style={{ padding: 4, background: "transparent", border: "none", color: "#64748b", cursor: "pointer" }}
          >
            <Copy size={13} />
          </button>
          <button
            title="Delete"
            onClick={() => onDelete(node.id)}
            style={{ padding: 4, background: "transparent", border: "none", color: "#ef4444", cursor: "pointer" }}
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
      {isOpen && hasChildren && node.children!.map((child) => (
        <NodeRow
          key={child.id}
          node={child}
          depth={depth + 1}
          expanded={expanded}
          toggle={toggle}
          selectedId={selectedId}
          onSelect={onSelect}
          onAddChild={onAddChild}
          onDuplicate={onDuplicate}
          onDelete={onDelete}
        />
      ))}
    </>
  );
}

export default function Routing() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["routing-tree"], queryFn: getRoutingTree });
  const tree = useMemo(() => data?.nodes ?? [], [data]);

  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const flat = useMemo(() => flatten(tree), [tree]);
  const selected = flat.find((n) => n.id === selectedId) ?? null;

  const [creatingUnder, setCreatingUnder] = useState<string | null | undefined>(undefined);
  const [newName, setNewName] = useState("");

  const createMut = useMutation({
    mutationFn: createRoutingNode,
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["routing-tree"] });
      setCreatingUnder(undefined);
      setNewName("");
      setSelectedId(created.id);
    },
  });

  const deleteMut = useMutation({
    mutationFn: ({ id, cascade }: { id: string; cascade: boolean }) =>
      deleteRoutingNode(id, cascade),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["routing-tree"] });
      setSelectedId(null);
    },
  });

  const dupMut = useMutation({
    mutationFn: duplicateRoutingNode,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routing-tree"] }),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<RoutingNode> }) =>
      updateRoutingNode(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routing-tree"] }),
  });

  const classifyMut = useMutation({
    mutationFn: () => startRoutingClassify({}),
    onSuccess: (r) => {
      alert(`Routing classification started.\nJob: ${r.job_id}\nPlan: ${r.plan_id}`);
    },
  });

  const toggle = (id: string) => {
    const next = new Set(expanded);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setExpanded(next);
  };

  const handleAddRoot = () => {
    setCreatingUnder(null);
    setNewName("");
  };

  const handleAddChild = (parentId: string) => {
    setCreatingUnder(parentId);
    const next = new Set(expanded);
    next.add(parentId);
    setExpanded(next);
    setNewName("");
  };

  const handleDelete = (id: string) => {
    const node = flat.find((n) => n.id === id);
    if (!node) return;
    const hasChildren = (node.children?.length ?? 0) > 0;
    const msg = hasChildren
      ? `Delete '${node.name}' and all its children?`
      : `Delete '${node.name}'?`;
    if (confirm(msg)) {
      deleteMut.mutate({ id, cascade: hasChildren });
    }
  };

  const submitCreate = () => {
    if (!newName.trim()) return;
    createMut.mutate({
      name: newName.trim(),
      parent_id: creatingUnder ?? null,
      is_leaf: true,
    });
  };

  return (
    <div style={{ padding: "32px 40px", maxWidth: 1400, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Routing tree</h1>
          <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
            Where should each photo go? Manage destinations, rules, and automation.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => classifyMut.mutate()}
            disabled={classifyMut.isPending}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "8px 16px", borderRadius: 8, border: "1px solid #334155",
              background: "#1e293b", color: "#22c55e", fontSize: 13, fontWeight: 600,
              cursor: classifyMut.isPending ? "wait" : "pointer",
            }}
          >
            <Play size={13} /> Run routing
          </button>
          <button
            onClick={handleAddRoot}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "8px 16px", borderRadius: 8, border: "none",
              background: "#1e40af", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer",
            }}
          >
            <Plus size={13} /> Add root
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 24 }}>
        <div style={{
          background: "#0f172a", border: "1px solid #1e293b",
          borderRadius: 12, padding: 16, minHeight: 400,
        }}>
          {isLoading ? (
            <div style={{ color: "#64748b", fontSize: 13 }}>Loading…</div>
          ) : tree.length === 0 ? (
            <div style={{ color: "#64748b", fontSize: 13 }}>
              No routing destinations yet. Click "Add root" to create your first one.
            </div>
          ) : (
            tree.map((n) => (
              <NodeRow
                key={n.id}
                node={n}
                depth={0}
                expanded={expanded}
                toggle={toggle}
                selectedId={selectedId}
                onSelect={setSelectedId}
                onAddChild={handleAddChild}
                onDuplicate={(id) => dupMut.mutate(id)}
                onDelete={handleDelete}
              />
            ))
          )}

          {creatingUnder !== undefined && (
            <div style={{
              marginTop: 16, padding: 12, borderRadius: 8,
              background: "#1e293b", border: "1px solid #334155",
            }}>
              <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>
                {creatingUnder ? `New child of '${flat.find((f) => f.id === creatingUnder)?.path}'` : "New root node"}
              </div>
              <input
                autoFocus
                placeholder="Name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submitCreate();
                  if (e.key === "Escape") setCreatingUnder(undefined);
                }}
                style={{ ...inputStyle, width: "100%", marginBottom: 8 }}
              />
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  onClick={submitCreate}
                  disabled={!newName.trim() || createMut.isPending}
                  style={{
                    padding: "6px 14px", borderRadius: 6, border: "none",
                    background: "#1e40af", color: "white", fontSize: 12, fontWeight: 600,
                    cursor: !newName.trim() ? "not-allowed" : "pointer",
                  }}
                >
                  Create
                </button>
                <button
                  onClick={() => setCreatingUnder(undefined)}
                  style={{
                    padding: "6px 14px", borderRadius: 6, border: "1px solid #334155",
                    background: "transparent", color: "#64748b", fontSize: 12, cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        <div style={{
          background: "#0f172a", border: "1px solid #1e293b",
          borderRadius: 12, padding: 0, minHeight: 400,
        }}>
          {selected ? (
            <RoutingLeafEditor
              key={selected.id}
              node={selected}
              onSave={(data) => updateMut.mutate({ id: selected.id, data })}
              saving={updateMut.isPending}
            />
          ) : (
            <div style={{
              display: "flex", flexDirection: "column", alignItems: "center",
              justifyContent: "center", height: 400, color: "#64748b", fontSize: 13,
            }}>
              <FolderTree size={36} color="#334155" />
              <div style={{ marginTop: 12 }}>Select a node to edit its settings.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function flatten(nodes: RoutingNode[]): RoutingNode[] {
  const out: RoutingNode[] = [];
  const walk = (n: RoutingNode) => {
    out.push(n);
    (n.children ?? []).forEach(walk);
  };
  nodes.forEach(walk);
  return out;
}
