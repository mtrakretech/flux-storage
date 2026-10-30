import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Check,
  ChevronDown,
  ChevronRight,
  File,
  Folder,
  FolderOpen,
  HardDrive,
  LoaderCircle,
  Search,
} from "lucide-react";
import {
  api,
  basename,
  bytes,
  number,
  type Item,
  type ManifestSummary,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";

type TreeItem = Item & { has_children?: boolean };
type Branch = { rows: TreeItem[]; total: number; root: TreeItem };

export function FolderTree({
  snapshotId,
  current,
  ancestors,
  onNavigate,
}: {
  snapshotId: string;
  current: string;
  ancestors: { id: string; path: string }[];
  onNavigate: (row: Item) => void;
}) {
  const [root, setRoot] = useState<TreeItem | null>(null),
    [branches, setBranches] = useState<Record<string, Branch>>({});
  const [expanded, setExpanded] = useState<Set<string>>(new Set()),
    [pending, setPending] = useState<Set<string>>(new Set()),
    [errors, setErrors] = useState<Record<string, string>>({});
  const cached = useRef<Record<string, Branch>>({}),
    epoch = useRef(0);
  const load = useCallback(async (id = "", offset = 0) => {
    const version = epoch.current;
    setPending((p) => new Set(p).add(id));
    setErrors((p) => ({ ...p, [id]: "" }));
    try {
      const result = await api<Branch>(
        "/api/tree?" +
          new URLSearchParams({ parent: id, offset: String(offset) }),
      );
      if (version !== epoch.current) return;
      if (!result.root) return;
      if (!id) {
        setRoot(result.root);
        setExpanded((p) => new Set(p).add(result.root.id));
      }
      const key = result.root.id;
      const next = {
        ...result,
        rows: offset
          ? [...(cached.current[key]?.rows || []), ...result.rows]
          : result.rows,
      };
      cached.current = { ...cached.current, [key]: next };
      setBranches(cached.current);
    } catch (error) {
      if (version === epoch.current)
        setErrors((p) => ({ ...p, [id]: (error as Error).message }));
    } finally {
      if (version === epoch.current)
        setPending((p) => {
          const next = new Set(p);
          next.delete(id);
          return next;
        });
    }
  }, []);
  useEffect(() => {
    epoch.current++;
    cached.current = {};
    setBranches({});
    setExpanded(new Set());
    setRoot(null);
    setErrors({});
    load();
  }, [snapshotId, load]);
  useEffect(() => {
    if (!root) return;
    setExpanded((p) => new Set([...p, ...ancestors.map((a) => a.id)]));
    for (const node of ancestors) if (!cached.current[node.id]) load(node.id);
  }, [ancestors, root?.id, load]);
  const toggle = (row: TreeItem) => {
    setExpanded((p) => {
      const next = new Set(p);
      if (next.has(row.id)) next.delete(row.id);
      else next.add(row.id);
      return next;
    });
    if (!cached.current[row.id]) load(row.id);
  };
  const keyboard = (event: KeyboardEvent<HTMLButtonElement>, row: TreeItem) => {
    const buttons = Array.from(
        event.currentTarget
          .closest('[role="tree"]')
          ?.querySelectorAll<HTMLButtonElement>('[role="treeitem"]') || [],
      ),
      position = buttons.indexOf(event.currentTarget);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      buttons[position + 1]?.focus();
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      buttons[position - 1]?.focus();
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      if (!expanded.has(row.id)) toggle(row);
      else buttons[position + 1]?.focus();
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      if (expanded.has(row.id)) toggle(row);
      else buttons.find((b) => b.dataset.node === row.parent)?.focus();
    }
    if (event.key === "Home") {
      event.preventDefault();
      buttons[0]?.focus();
    }
    if (event.key === "End") {
      event.preventDefault();
      buttons.at(-1)?.focus();
    }
  };
  const node = (row: TreeItem, depth = 0): React.ReactNode => {
    const open = expanded.has(row.id),
      branch = branches[row.id],
      hasChildren = row.id === root?.id || row.has_children;
    return (
      <div key={row.id} role="none">
        <div
          className={cn(
            "folder-tree-line",
            current === row.id && "tree-current",
          )}
          style={{ paddingLeft: 8 + depth * 15 }}
        >
          <button
            className="tree-expander"
            aria-label={`${open ? "Collapse" : "Expand"} ${basename(row.path)}`}
            onClick={() => toggle(row)}
            disabled={!hasChildren}
          >
            {pending.has(row.id) ? (
              <LoaderCircle className="size-3 animate-spin" />
            ) : hasChildren ? (
              open ? (
                <ChevronDown className="size-3" />
              ) : (
                <ChevronRight className="size-3" />
              )
            ) : null}
          </button>
          <button
            role="treeitem"
            aria-level={depth + 1}
            aria-selected={current === row.id}
            aria-expanded={hasChildren ? open : undefined}
            data-node={row.path}
            onKeyDown={(event) => keyboard(event, row)}
            onClick={() => onNavigate(row)}
            onDoubleClick={() => toggle(row)}
            className="tree-name"
            title={row.path}
          >
            {row.id === root?.id ? (
              <HardDrive className="size-3.5" />
            ) : open ? (
              <FolderOpen className="size-3.5" />
            ) : (
              <Folder className="size-3.5" />
            )}
            <span>{basename(row.path)}</span>
          </button>
        </div>
        {open && (
          <div role="group">
            {branch?.rows.map((child) => node(child, depth + 1))}
            {errors[row.id] && (
              <button
                className="tree-error"
                onClick={() => load(row.id)}
                title={errors[row.id] || "Read failed"}
              >
                Read failed · {errors[row.id] || "please retry"} · Retry
              </button>
            )}
            {branch && branch.rows.length < branch.total && (
              <button
                className="tree-load-more"
                onClick={() => load(row.id, branch.rows.length)}
              >
                Load more ({branch.total - branch.rows.length})
              </button>
            )}
            {branch && !branch.rows.length && (
              <p
                className="tree-empty"
                style={{ paddingLeft: 31 + depth * 15 }}
              >
                No subfolders
              </p>
            )}
          </div>
        )}
      </div>
    );
  };
  return (
    <aside className="folder-tree">
      <div className="folder-tree-heading">
        <FolderOpen className="size-3.5" />
        FOLDERS<span>Expand to explore</span>
      </div>
      <div
        role="tree"
        aria-label="Folder navigation tree"
        className="folder-tree-scroll"
      >
        {root ? (
          node(root)
        ) : (
          <div className="p-4 text-xs text-muted-foreground">
            {errors[""] ? (
              <button onClick={() => load()} title={errors[""]}>
                Could not load tree · {errors[""] || "please retry"} · Retry
              </button>
            ) : (
              <LoaderCircle className="size-4 animate-spin" />
            )}
          </div>
        )}
      </div>
    </aside>
  );
}

export function ExplorerGrid({
  rows,
  selected,
  canSelect,
  onSelect,
  onBrowse,
  onInspect,
  loading,
}: {
  rows: Item[];
  selected: Map<string, Item>;
  canSelect: (row: Item) => boolean;
  onSelect: (row: Item, value: boolean) => void;
  onBrowse: (row: Item) => void;
  onInspect: (row: Item) => void;
  loading: boolean;
}) {
  return (
    <div
      className={cn("explorer-grid", loading && "opacity-60")}
      role="list"
      aria-label="Explorer icon view"
    >
      {rows.map((row) => (
        <div
          key={row.id}
          role="listitem"
          className={cn(
            "explorer-tile",
            selected.has(row.id) && "tile-selected",
          )}
          data-testid="explorer-tile"
        >
          <Checkbox
            checked={selected.has(row.id)}
            disabled={!canSelect(row) || loading}
            onCheckedChange={(value) => onSelect(row, !!value)}
            aria-label={`Select ${basename(row.path)}`}
            className="absolute left-3 top-3"
          />
          <button
            className="tile-content"
            onClick={() => {if(canSelect(row)&&!loading)onSelect(row,!selected.has(row.id))}}
            onDoubleClick={() => (row.is_file ? onInspect(row) : onBrowse(row))}
            aria-label={`Item ${basename(row.path)}`}
          >
            <span className={cn("tile-icon", row.is_file && "tile-file")}>
              {row.is_file ? <File /> : <Folder />}
            </span>
            <strong title={row.path}>{basename(row.path)}</strong>
            <span>{bytes(row.bytes)}</span>
            <small>{row.is_file ? "File" : number(row.files) + " files"}</small>
          </button>
          {!row.is_file && (
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => onBrowse(row)}
              className="absolute right-2 top-2"
              aria-label={`Browse ${basename(row.path)}`}
            >
              <ChevronRight />
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}

export function ExplorerNavigation({
  folder,
  ancestors,
  onNavigate,
  onResolve,
  onBack,
  onForward,
  canBack,
  canForward,
}: {
  folder?: Item;
  ancestors: { id: string; path: string }[];
  onNavigate: (row: { id: string; path: string }) => void;
  onResolve: (path: string) => void;
  onBack: () => void;
  onForward: () => void;
  canBack: boolean;
  canForward: boolean;
}) {
  const [editing, setEditing] = useState(false),
    [path, setPath] = useState(folder?.path || "");
  useEffect(() => {
    setPath(folder?.path || "");
    setEditing(false);
  }, [folder?.path]);
  return (
    <div className="explorer-navigation">
      <div className="flex shrink-0 gap-0.5">
        <Button
          variant="ghost"
          size="icon-sm"
          disabled={!canBack}
          onClick={onBack}
          aria-label="Back"
        >
          <ArrowLeft />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          disabled={!canForward}
          onClick={onForward}
          aria-label="Forward"
        >
          <ArrowRight />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          disabled={ancestors.length < 2}
          onClick={() => onNavigate(ancestors[ancestors.length - 2])}
          aria-label="Parent folder"
        >
          <ArrowUp />
        </Button>
      </div>
      <div className="explorer-address" onDoubleClick={() => setEditing(true)}>
        {editing ? (
          <Input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            autoFocus
            aria-label="Folder address"
            onBlur={() => setEditing(false)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                onResolve(path);
                setEditing(false);
              }
              if (e.key === "Escape") setEditing(false);
            }}
          />
        ) : (
          <>
            <HardDrive className="size-3.5 shrink-0 text-muted-foreground" />
            <div className="address-crumbs">
              {ancestors.map((a) => (
                <span key={a.id}>
                  <ChevronRight className="size-3" />
                  <button onClick={() => onNavigate(a)}>
                    {basename(a.path)}
                  </button>
                </span>
              ))}
            </div>
            <button
              className="ml-auto shrink-0 rounded px-1 text-[10px] text-muted-foreground hover:text-foreground"
              onClick={() => setEditing(true)}
              aria-label="Edit folder address"
            >
              Edit path
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export function DeletionManifest({
  ticket,
  summary,
}: {
  ticket: string;
  summary: ManifestSummary;
}) {
  const [rows, setRows] = useState<
      { path: string; kind: string; bytes: number; action: string }[]
    >([]),
    [total, setTotal] = useState(summary.entries),
    [offset, setOffset] = useState(0);
  const [query, setQuery] = useState(""),
    [search, setSearch] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(query);
      setOffset(0);
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    const controller = new AbortController();
    setBusy(true);
    setError("");
    api<{ rows: typeof rows; total: number }>(
      "/api/preview/" +
        encodeURIComponent(ticket) +
        "/manifest?" +
        new URLSearchParams({ offset: String(offset), q: search }),
      undefined,
      controller.signal,
    )
      .then((result) => {
        setRows(result.rows);
        setTotal(result.total);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [ticket, offset, search]);
  return (
    <details className="deletion-manifest" open>
      <summary>
        <FilesIcon />
        {number(summary.files)} files + {number(summary.folders)} folders will
        be removed
        <ChevronDown className="ml-auto size-3.5" />
      </summary>
      <div className="manifest-tools">
        <div className="flex flex-1 items-center gap-2">
          <Search className="size-3.5 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Find an exact file in this deletion…"
            aria-label="Search deletion manifest"
          />
        </div>
        <Button asChild variant="outline" size="sm">
          <a
            href={`/api/preview/${encodeURIComponent(ticket)}/manifest?format=csv`}
          >
            Full CSV
          </a>
        </Button>
      </div>
      <div className="manifest-entries">
        {busy ? (
          <div className="flex items-center gap-2 p-4 text-xs">
            <LoaderCircle className="size-3 animate-spin" />
            Reading exact paths…
          </div>
        ) : error ? (
          <p role="alert" className="p-4 text-xs text-destructive">
            {error}
          </p>
        ) : (
          rows.map((row) => (
            <div key={row.path} className="manifest-entry">
              {row.kind === "folder" ? (
                <Folder className="size-3.5" />
              ) : (
                <File className="size-3.5" />
              )}
              <div>
                <code>{row.path}</code>
                <span>{row.action}</span>
              </div>
              <small>{row.kind === "file" ? bytes(row.bytes) : "Folder"}</small>
            </div>
          ))
        )}
      </div>
      <div className="manifest-pagination">
        <span>
          {total
            ? `${offset + 1}–${Math.min(offset + 100, total)} of ${number(total)}`
            : "No matching entries"}
        </span>
        <Button
          variant="ghost"
          size="icon-xs"
          disabled={!offset || busy}
          onClick={() => setOffset(Math.max(0, offset - 100))}
          aria-label="Previous manifest page"
        >
          <ArrowLeft />
        </Button>
        <Button
          variant="ghost"
          size="icon-xs"
          disabled={offset + 100 >= total || busy}
          onClick={() => setOffset(offset + 100)}
          aria-label="Next manifest page"
        >
          <ArrowRight />
        </Button>
      </div>
    </details>
  );
}
function FilesIcon() {
  return <Check className="size-3.5 shrink-0" />;
}
