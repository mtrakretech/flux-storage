import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity as ActivityIcon,
  ArrowDown,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  ArrowUpDown,
  Box,
  Check,
  ChevronRight,
  CircleAlert,
  Clock3,
  Database,
  Ellipsis,
  ExternalLink,
  File,
  Files,
  Folder,
  FolderOpen,
  HardDrive,
  Info,
  LayoutDashboard,
  LoaderCircle,
  Menu,
  Monitor,
  Moon,
  Package,
  Play,
  Power,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  ShieldOff,
  SlidersHorizontal,
  Sparkles,
  Square,
  Sun,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  ApprovalCard,
  FilterChips,
  LoadingState,
  PathBlock,
  Recommendation,
  TaskRow,
} from "@/components/beautiful";
import {
  api,
  basename,
  bytes,
  date,
  number,
  type Activity,
  type Item,
  type Listing,
  type Mode,
  type Overview,
  type Preview,
  type Status,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { LayoutGrid, List, PanelLeft, LockKeyhole } from "lucide-react";
import {
  FolderTree,
  ExplorerGrid,
  ExplorerNavigation,
  DeletionManifest,
} from "@/components/explorer";
import { StorageDashboard, ConnectionSettings } from '@/components/storage-dashboard';

const navItems = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "tree", label: "File explorer", icon: FolderOpen },
  { id: "dependencies", label: "Dependencies", icon: Package },
  { id: "generated", label: "Build artifacts", icon: Box },
  { id: "caches", label: "Caches", icon: Database },
  { id: "large", label: "Large files", icon: Files },
  { id: "review", label: "Tooling & review", icon: SlidersHorizontal },
  { id: "issues", label: "Scan issues", icon: CircleAlert },
  { id: "activity", label: "Activity", icon: ActivityIcon },
];
const captions: Record<string, string> = {
  overview: "Understand your storage. Make space with confidence.",
  tree: "Browse folders, inspect files, and choose exactly what to manage.",
  dependencies:
    "Project dependencies and bundled runtimes. Not automatically unused.",
  generated: "Compiled output, generated assets and local build directories.",
  caches: "Recognized caches, separated from saved data and credentials.",
  large: "Your largest individual files. Inspect before manually removing.",
  review: "SDKs, Git histories, offline data and shared development tooling.",
  issues:
    "See exactly where a scan could not read. Administrator does not override every Windows protection.",
  activity:
    "A transparent record of your scans, approvals and cleanup results.",
};
const chartColors = [
  "var(--chart-3)",
  "var(--chart-2)",
  "var(--chart-1)",
  "var(--chart-4)",
  "var(--chart-5)",
  "#a1a1aa",
  "#d4d4d8",
];
const emptyListing: Listing = { rows: [], total: 0 };
type Theme = "light" | "dark" | "system";

export default function App() {
  const [view, setView] = useState("overview"),
    [mode, setMode] = useState<Mode>("recommended");
  const [status, setStatus] = useState<Status | null>(null),
    [overview, setOverview] = useState<Overview | null>(null);
  const [offline, setOffline] = useState(""),
    [toast, setToast] = useState(""),
    [mobileNav, setMobileNav] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return (localStorage.getItem("flux-theme") as Theme) || "light";
    } catch {
      return "light";
    }
  });
  const [listing, setListing] = useState<Listing>(emptyListing),
    [loading, setLoading] = useState(false),
    [listError, setListError] = useState("");
  const [query, setQuery] = useState(""),
    [debounced, setDebounced] = useState(""),
    [offset, setOffset] = useState(0);
  const [parent, setParent] = useState(""),
    [sort, setSort] = useState("bytes"),
    [direction, setDirection] = useState("desc");
  const [filter, setFilter] = useState("all"),
    [nested, setNested] = useState(false),
    [old, setOld] = useState(false),
    [reload, setReload] = useState(0);
  const [selected, setSelected] = useState<Map<string, Item>>(new Map()),
    [detail, setDetail] = useState<Item | null>(null);
  const [scanOpen, setScanOpen] = useState(false),
    [scanRoot, setScanRoot] = useState(""),
    [actionBusy, setActionBusy] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false),
    [preview, setPreview] = useState<Preview | null>(null),
    [previewBusy, setPreviewBusy] = useState(false),
    [previewError, setPreviewError] = useState("");
  const [confirmation, setConfirmation] = useState(""),
    [ack, setAck] = useState(false);
  const [unlockOpen, setUnlockOpen] = useState(false),
    [unlockText, setUnlockText] = useState(""),
    [unlockAck, setUnlockAck] = useState(false);
  const [layout, setLayout] = useState<"list" | "grid">("list"),
    [showTree, setShowTree] = useState(true);
  const folderHistory = useRef<string[]>([""]),
    [historyPosition, setHistoryPosition] = useState(0);
  const [events, setEvents] = useState<Activity[]>([]),
    [issues, setIssues] = useState<{ path: string; error: string }[]>([]);
  const previousJob = useRef<Status["job"] | null>(null),
    previousSnapshot = useRef(""),
    searchRef = useRef<HTMLInputElement>(null);
  const selectedDrive=useRef(''),preferencesLoaded=useRef(false);
  const [driveSelection,setDriveSelection]=useState('');
  const busy = status?.job.status === "running",
    snapshot = status?.snapshot;
  const notify = useCallback((message: string) => setToast(message), []);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 6500);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      document.documentElement.classList.toggle(
        "dark",
        theme === "dark" || (theme === "system" && media.matches),
      );
      try {
        localStorage.setItem("flux-theme", theme);
      } catch {
        /* Private mode storage can be unavailable. */
      }
    };
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme]);
  const refresh = useCallback(async () => {
    const data = await api<Status>("/api/status?"+new URLSearchParams({drive:selectedDrive.current}));
    if(!preferencesLoaded.current){preferencesLoaded.current=true;setTheme(data.preferences.theme);setScanRoot(data.snapshot?.root||data.roots[0]||'');}
    setStatus(data);
    setOffline("");
    const previous = previousJob.current;
    if (previous?.status === "running" && data.job.status !== "running") {
      if (data.job.status === "error")
        notify(
          data.job.error || "The operation failed. See Activity for details.",
        );
      if (data.job.status === "completed" && data.job.kind === "cleanup")
        notify(
          `Cleanup finished. Actual free-space change: ${bytes(data.job.recovered_bytes)}. Rescan to update the inventory.`,
        );
      if (data.job.status === "completed" && data.job.kind === "scan")
        notify("Scan complete. Your inventory is ready.");
      if (data.job.status === "cancelled")
        notify("Scan cancelled. The previous completed inventory was kept.");
    }
    previousJob.current = data.job;
    if (data.snapshot?.id !== previousSnapshot.current) {
      previousSnapshot.current = data.snapshot?.id || "";
      setSelected(new Map());
      setParent("");
      setOffset(0);
      folderHistory.current = [""];
      setHistoryPosition(0);
    }
    return data;
  }, [notify]);
  useEffect(() => {
    let active = true,
      timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      let delay = 6000;
      try {
        const data = await refresh();
        delay = data.job.status === "running" ? 1200 : 6000;
      } catch (e) {
        if (active)
          setOffline(
            e instanceof Error
              ? e.message
              : "Cannot connect to the local server.",
          );
        delay = 5000;
      }
      if (active) timer = setTimeout(poll, delay);
    };
    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [refresh]);
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(query);
      setOffset(0);
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    if (!snapshot) return;
    const controller = new AbortController();
    api<Overview>("/api/overview", undefined, controller.signal)
      .then(setOverview)
      .catch((e) => {
        if (e.name !== "AbortError") notify(e.message);
      });
    return () => controller.abort();
  }, [snapshot?.id, notify]);
  const tableView = !["overview", "activity", "issues"].includes(view);
  useEffect(() => {
    if (!tableView || !snapshot) return;
    const controller = new AbortController();
    setLoading(true);
    setListError("");
    const params = new URLSearchParams({
      view,
      mode,
      parent,
      q: debounced,
      offset: String(offset),
      limit: "50",
      nested: nested ? "1" : "0",
      old: old ? "1" : "0",
      eligible: filter === "eligible" ? "1" : "0",
      sort,
      direction,
    });
    api<Listing>("/api/items?" + params, undefined, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setListing(data);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setListError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [
    view,
    mode,
    parent,
    debounced,
    offset,
    nested,
    old,
    filter,
    sort,
    direction,
    reload,
    snapshot?.id,
    tableView,
  ]);
  useEffect(() => {
    const controller = new AbortController();
    if (view === "activity")
      api<{ events: Activity[] }>("/api/activity", undefined, controller.signal)
        .then((d) => setEvents(d.events))
        .catch((e) => {
          if (e.name !== "AbortError") notify(e.message);
        });
    if (view === "issues")
      api<{ errors: { path: string; error: string }[] }>(
        "/api/errors",
        undefined,
        controller.signal,
      )
        .then((d) => setIssues(d.errors))
        .catch((e) => {
          if (e.name !== "AbortError") notify(e.message);
        });
    return () => controller.abort();
  }, [view, reload, status?.job.status, notify]);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "k") {
        event.preventDefault();
        if (!tableView) setView("tree");
        setTimeout(() => searchRef.current?.focus(), 0);
      }
      if (event.key === "Escape") setMobileNav(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [tableView]);

  const navigate = (next: string) => {
    setView(next);
    setOffset(0);
    setQuery("");
    setDebounced("");
    setParent("");
    setFilter("all");
    setMobileNav(false);
    folderHistory.current = [""];
    setHistoryPosition(0);
  };
  const browse = (row: Item | { id: string; path: string }) => {
    if (row.id !== parent) {
      folderHistory.current = [
        ...folderHistory.current.slice(0, historyPosition + 1),
        row.id,
      ];
      setHistoryPosition(folderHistory.current.length - 1);
    }
    setView("tree");
    setParent(row.id);
    setOffset(0);
    setQuery("");
    setDebounced("");
    setDetail(null);
    setFilter("all");
  };
  const goHistory = (delta: number) => {
    const next = historyPosition + delta;
    if (next < 0 || next >= folderHistory.current.length) return;
    setHistoryPosition(next);
    setParent(folderHistory.current[next]);
    setOffset(0);
    setQuery("");
    setDebounced("");
  };
  const resolvePath = async (path: string) => {
    try {
      const result = await api<{ item: Item }>(
        "/api/resolve-path?" + new URLSearchParams({ path }),
      );
      browse(result.item);
    } catch (e) {
      notify((e as Error).message);
    }
  };
  const changeMode = (next: Mode) => {
    setMode(next);
    setPreviewOpen(false);
    setPreview(null);
    setDetail(null);
    setOffset(0);
  };
  const requestFullControl = () => {
    if (status?.full_control_enabled) {
      changeMode("full");
      return;
    }
    setUnlockText("");
    setUnlockAck(false);
    setUnlockOpen(true);
  };
  const unlock = async () => {
    setActionBusy(true);
    try {
      await api("/api/full-control", {
        enabled: true,
        confirmation: unlockText,
        acknowledge: unlockAck,
      });
      await refresh();
      changeMode("full");
      setUnlockOpen(false);
      notify(
        "Risky full control is enabled for this server session. No files have been deleted.",
      );
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setActionBusy(false);
    }
  };
  const inspect = async (row: Item) => {
    setDetail(row);
    try {
      const result = await api<{ item: Item }>(
        "/api/item/" + row.id + "?mode=" + mode,
      );
      setDetail((current) => (current?.id === row.id ? result.item : current));
    } catch (e) {
      notify((e as Error).message);
    }
  };
  const reveal = async (row: Item) => {
    try {
      await api("/api/reveal", { id: row.id });
    } catch (e) {
      notify((e as Error).message);
    }
  };
  const copy = async (path: string) => {
    try {
      await navigator.clipboard.writeText(path);
      notify("Path copied.");
    } catch {
      notify(
        "Clipboard is unavailable. Select the path in the details panel and copy it manually.",
      );
    }
  };
  // Selection is not deletion permission: every item can be reviewed, even when
  // the current mode blocks its removal. The preview reports blocked targets.
  const canSelect = (_row: Item) => !busy && !offline;
  const toggle = (row: Item, checked: boolean) => {
    setSelected((previous) => {
      const next = new Map(previous);
      if (checked && next.size < 500) next.set(row.id, row);
      else next.delete(row.id);
      return next;
    });
  };
  const sortBy = (column: string) => {
    if (sort === column) setDirection(direction === "desc" ? "asc" : "desc");
    else {
      setSort(column);
      setDirection(column === "path" ? "asc" : "desc");
    }
    setOffset(0);
  };
  const prepare = async (ids?: string[]) => {
    setPreviewOpen(true);
    setPreview(null);
    setPreviewError("");
    setPreviewBusy(true);
    setConfirmation("");
    setAck(false);
    try {
      setPreview(
        await api<Preview>("/api/preview", {
          ids: ids || [...selected.keys()],
          mode,
          review_blocked: true,
        }),
      );
    } catch (e) {
      setPreviewError((e as Error).message);
    } finally {
      setPreviewBusy(false);
    }
  };
  const removeBlocked = () => {
    if (!preview) return;
    const blockedIds = new Set(preview.blocked.map((row) => row.id));
    const next = new Map([...selected].filter(([id]) => !blockedIds.has(id)));
    setSelected(next);
    if (next.size) prepare([...next.keys()]);
    else {
      setPreviewOpen(false);
      notify(
        "No removable selections remain. Choose another mode or selection.",
      );
    }
  };
  const cleanup = async () => {
    if (!preview) return;
    setActionBusy(true);
    try {
      await api("/api/cleanup", {
        ticket: preview.ticket,
        confirmation,
        acknowledge: ack,
      });
      setPreviewOpen(false);
      setSelected(new Map());
      await refresh();
    } catch (e) {
      setPreviewError((e as Error).message);
    } finally {
      setActionBusy(false);
    }
  };
  const startScan = async () => {
    setActionBusy(true);
    try {
      await api("/api/scan", { root: scanRoot.trim() });
      setScanOpen(false);
      await refresh();
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setActionBusy(false);
    }
  };
  const cancel = async () => {
    try {
      await api("/api/cancel", {});
      notify("Cancellation requested.");
    } catch (e) {
      notify((e as Error).message);
    }
  };
  const allPage = listing.rows.filter(canSelect),
    allChecked = allPage.length > 0 && allPage.every((r) => selected.has(r.id));
  const usage = status?.disk.total ? Math.min(1,Math.max(0,status.disk.used / status.disk.total)) : 0;
  const counts = overview?.counts || {};
  const title =
    view === "overview"
      ? "Your storage, in focus."
      : navItems.find((n) => n.id === view)?.label || "Storage";

  return (
    <TooltipProvider>
      <div className="app-shell">
        {mobileNav && (
          <button
            className="fixed inset-0 z-30 bg-black/30 lg:hidden"
            aria-label="Close navigation"
            onClick={() => setMobileNav(false)}
          />
        )}
        <aside className={cn("app-sidebar", mobileNav && "sidebar-visible")}>
          <button onClick={() => navigate("overview")} className="brand">
            <span className="brand-mark">
              <Zap className="size-5" fill="currentColor" />
            </span>
            <span>
              flux
              <span className="ml-1.5 font-normal text-muted-foreground">
                storage
              </span>
            </span>
            <Badge variant="outline" className="ml-auto text-[9px]">
              {status?.version||'dev'}
            </Badge>
          </button>
          <div className="workspace-switch">
            <div className="grid size-8 place-items-center rounded-lg border bg-background">
              <Monitor className="size-4" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold">This computer</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">
                Windows · Local workspace
              </p>
            </div>
            <ShieldCheck className="ml-auto size-4 text-muted-foreground" />
          </div>
          <p className="nav-label">WORKSPACE</p>
          <nav aria-label="Main navigation">
            {navItems.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                data-view={id}
                onClick={() => navigate(id)}
                className={cn("nav-item", view === id && "nav-active")}
              >
                <Icon className="size-4" />
                <span>{label}</span>
                {counts[id] !== undefined && (
                  <span className="nav-count">{number(counts[id])}</span>
                )}
                {id === "issues" && !!snapshot?.error_count && (
                  <span className="nav-count">{snapshot.error_count}</span>
                )}
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="rounded-lg border bg-background/70 p-3">
              <div className="mb-2 flex items-center gap-2 text-xs font-medium">
                <ShieldCheck className="size-3.5" />
                Private by design
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                Your files never leave this computer. You approve every
                deletion.
              </p>
            </div>
            <div className="mt-4 flex items-center justify-between text-[10px] text-muted-foreground">
              <span title={status?.connection.url}>{status?.connection.port?`Port ${status.connection.port}`:'Connecting…'} · Local only · MTR Soft</span>
              <span className="flex items-center gap-1.5">
                <i
                  className={cn(
                    "size-1.5 rounded-full",
                    offline ? "bg-destructive" : "bg-chart-3",
                  )}
                />
                {offline ? "Offline" : "Connected"}
              </span>
            </div>
          </div>
        </aside>

        <div className="app-main">
          <header className="topbar">
            <div className="flex min-w-0 items-center gap-3">
              <Button
                variant="ghost"
                size="icon-sm"
                className="lg:hidden"
                onClick={() => setMobileNav(!mobileNav)}
                aria-label="Toggle navigation"
              >
                <Menu />
              </Button>
              <HardDrive className="hidden size-4 text-muted-foreground sm:block" />
              <span className="text-xs text-muted-foreground">Workspace</span>
              <ChevronRight className="size-3 text-muted-foreground" />
              <span className="truncate text-xs font-medium">
                {view === "overview" ? "Overview" : title}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className="hidden gap-1.5 px-2.5 py-1 text-[10px] sm:flex"
              >
                {status?.is_admin ? (
                  <ShieldCheck className="size-3" />
                ) : (
                  <ShieldOff className="size-3" />
                )}
                {status?.is_admin ? "Administrator" : "Limited access"}
              </Badge>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Change color theme"
                  >
                    {theme === "dark" ? (
                      <Moon />
                    ) : theme === "system" ? (
                      <Monitor />
                    ) : (
                      <Sun />
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {(["light", "dark", "system"] as Theme[]).map((t) => (
                    <DropdownMenuItem key={t} onClick={() => {setTheme(t);api('/api/preferences',{theme:t}).catch(e=>notify(e.message));}}>
                      {t === "light" ? (
                        <Sun />
                      ) : t === "dark" ? (
                        <Moon />
                      ) : (
                        <Monitor />
                      )}
                      <span className="capitalize">{t}</span>
                      {theme === t && <Check className="ml-auto" />}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Application options"
                  >
                    <Settings2 />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    onClick={() =>
                      api("/api/windows-apps", {}).catch((e) =>
                        notify(e.message),
                      )
                    }
                  >
                    <ExternalLink />
                    Windows app management
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() =>
                      api("/api/system-tool", {
                        name: "storage-settings",
                      }).catch((e) => notify(e.message))
                    }
                  >
                    <HardDrive />
                    Windows storage settings
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() =>
                      api("/api/system-tool", {
                        name: "indexing-options",
                      }).catch((e) => notify(e.message))
                    }
                  >
                    <Search />
                    Windows indexing options
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() =>
                      api("/api/system-tool", { name: "disk-cleanup" }).catch(
                        (e) => notify(e.message),
                      )
                    }
                  >
                    <Database />
                    Windows Disk Cleanup
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate("issues")}>
                    <CircleAlert />
                    View scan issues
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    disabled={!!busy}
                    onClick={() => {
                      api("/api/shutdown", {})
                        .then(() =>
                          setOffline(
                            "Flux was stopped. Reopen the desktop shortcut to start it again.",
                          ),
                        )
                        .catch((e) => notify(e.message));
                    }}
                  >
                    <Power />
                    Stop local server
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          <main className="main-content">
            {offline && (
              <div
                className="notice-box border-destructive/30 bg-destructive/5 text-destructive"
                role="alert"
              >
                <CircleAlert className="size-4 shrink-0" />
                <span className="flex-1">
                  {offline} Your last inventory is preserved.
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => refresh().catch((e) => setOffline(e.message))}
                >
                  Retry
                </Button>
              </div>
            )}
            <div className="page-heading">
              <div>
                <div className="eyebrow">LOCAL DISK INTELLIGENCE</div>
                <h1>{title}</h1>
                <p>{captions[view]}</p>
              </div>
              <div className="flex shrink-0 gap-2">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      className="hidden sm:flex"
                      disabled={!snapshot}
                    >
                      <ArrowDownToLine />
                      Export
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() =>
                        window.location.assign("/api/export?kind=dependencies")
                      }
                    >
                      Dependency & build paths CSV
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        window.location.assign("/api/export?kind=all")
                      }
                    >
                      Complete folder inventory CSV
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <Button
                  onClick={() => setScanOpen(true)}
                  disabled={!!busy || !!offline}
                  data-testid="new-scan"
                >
                  <RefreshCw className={cn(busy && "animate-spin")} />
                  {busy ? "Working…" : "New scan"}
                </Button>
              </div>
            </div>

            {busy && (
              <section className="operation-card" aria-live="polite">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <LoadingState
                    label={status?.job.phase || "Working"}
                    started={status?.job.started}
                  />
                  {status?.job.kind === "scan" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={cancel}
                      disabled={status.job.phase === "Saving inventory"}
                    >
                      <Square className="size-3" />
                      Cancel scan
                    </Button>
                  )}
                </div>
                <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted-foreground">
                  {status?.job.kind === "scan" ? (
                    <>
                      <span>{number(status.job.files)} files</span>
                      <span>{number(status.job.directories)} folders</span>
                    </>
                  ) : (
                    <span>
                      {status?.job.completed || 0} / {status?.job.total || 0}{" "}
                      selections completed
                    </span>
                  )}
                  <span>No file contents uploaded</span>
                </div>
                <p
                  className="mt-3 truncate font-mono text-[11px] text-muted-foreground"
                  title={status?.job.current}
                >
                  {status?.job.current}
                </p>
                <div className="indeterminate-track mt-4">
                  <i />
                </div>
              </section>
            )}
            {status?.needs_rescan && (
              <div className="notice-box border-chart-3/30 bg-chart-1/10">
                <Info className="size-4 shrink-0" />
                <span className="flex-1">
                  Cleanup changed your files. Folder sizes below are historical;
                  new previews recheck selected items live. Rescan to refresh the overview.
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setScanOpen(true)}
                  disabled={!!busy}
                >
                  Rescan
                </Button>
              </div>
            )}

            <section className={cn("metric-grid",view==="tree"&&"explorer-metrics")} aria-label="Storage metrics">
              {[
                {
                  label: "Available space",
                  value: bytes(status?.disk.free),
                  detail: status
                    ? (status.disk.ready?`${Math.round((1 - usage) * 100)}% free · ${status.disk.path}`:status.disk.status||'Checking storage')
                    : "Reading system drive",
                  icon: HardDrive,
                },
                {
                  label: "Reviewable cleanup",
                  value: bytes(snapshot?.candidate_bytes),
                  detail: snapshot
                    ? `${number(snapshot.candidate_count)} recommended targets · logical size`
                    : "Scan to discover candidates",
                  icon: Sparkles,
                },
                {
                  label: "Files analyzed",
                  value: snapshot ? number(snapshot.file_count) : "—",
                  detail: snapshot
                    ? `${number(snapshot.directory_count)} folders inventoried`
                    : "No completed scan",
                  icon: Files,
                },
                {
                  label: "Latest scan",
                  value: snapshot ? date(snapshot.scanned_at) : "Not scanned",
                  detail: snapshot
                    ? `${snapshot.root} · ${Math.round(snapshot.elapsed)} seconds`
                    : "Start a metadata-only scan",
                  icon: Clock3,
                },
              ].map(({ label, value, detail, icon: Icon }) => (
                <div className="metric-card" key={label}>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{label}</span>
                    <Icon className="size-3.5" />
                  </div>
                  {status ? (
                    <strong>{value}</strong>
                  ) : (
                    <Skeleton className="my-3 h-7 w-28" />
                  )}
                  <p>{detail}</p>
                </div>
              ))}
            </section>

            {view === "overview" && (
              <div className="space-y-6">
                <StorageDashboard status={status} selected={driveSelection||status?.disk.path||''} onSelect={path=>{selectedDrive.current=path;setDriveSelection(path);refresh().catch(e=>notify(e.message));}} onScan={path=>{setScanRoot(path);setScanOpen(true);}}/>
                {status&&<ConnectionSettings status={status} onSaved={()=>{refresh().catch(e=>notify(e.message));}} notify={notify}/>}
                <div className="overview-grid">
                  <section className="panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Storage overview</h2>
                        <p>{status?.disk.label||'Selected volume'}, at a glance.</p>
                      </div>
                      <Badge variant="outline" className="text-[10px]">
                         {status?.disk.path||'Discovering…'}
                      </Badge>
                    </div>
                    <div className="drive-summary">
                      <div className="drive-donut">
                        <svg
                          viewBox="0 0 160 160"
                          aria-label={`${Math.round(usage * 100)} percent used`}
                        >
                          <circle
                            className="donut-track"
                            cx="80"
                            cy="80"
                            r="65"
                          />
                          <circle
                            className="donut-fill"
                            cx="80"
                            cy="80"
                            r="65"
                            strokeDasharray={`${usage * 408.4} 408.4`}
                          />
                        </svg>
                        <div>
                          <strong>
                            {Math.round(usage * 100)}
                            <span>%</span>
                          </strong>
                          <small>used</small>
                        </div>
                      </div>
                      <div className="space-y-5">
                        <div>
                          <span className="text-xs text-muted-foreground">
                            Used storage
                          </span>
                          <p className="mt-1 text-2xl font-semibold tracking-tight">
                            {bytes(status?.disk.used)}
                            <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                              / {bytes(status?.disk.total)}
                            </span>
                          </p>
                        </div>
                        <div className="flex gap-6 text-xs">
                          <span className="flex items-center gap-2">
                            <i className="size-2 rounded-full bg-chart-3" />
                            Used
                          </span>
                          <span className="flex items-center gap-2 text-muted-foreground">
                            <i className="size-2 rounded-full bg-muted-foreground/25" />
                            Free · {bytes(status?.disk.free)}
                          </span>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {if(status?.disk.ready){setScanRoot(status.disk.path);setScanOpen(true);}else notify('Wait for the selected volume to become ready.');}}
                        >
                           Scan selected volume
                          <ArrowRight className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                    <div className="border-t px-5 py-3 text-[11px] text-muted-foreground">
                      Actual drive usage. Folder totals may differ because of
                      hardlinks and compression.
                    </div>
                  </section>
                  <section className="panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Largest user folders</h2>
                        <p>Current inventory: {snapshot?.root||'not scanned'} · click to explore.</p>
                      </div>
                      <Folder className="size-4 text-muted-foreground" />
                    </div>
                    <div className="space-y-4 px-5 pb-5">
                      {!overview ? (
                        <>
                          {[1, 2, 3, 4].map((n) => (
                            <Skeleton key={n} className="h-8 w-full" />
                          ))}
                        </>
                      ) : overview.breakdown.length ? (
                        overview.breakdown.slice(0, 5).map((row, i) => (
                          <button
                            className="folder-bar group"
                            key={row.id}
                            onClick={() => browse(row)}
                          >
                            <div>
                              <span className="flex items-center gap-2">
                                <Folder className="size-3.5 text-muted-foreground" />
                                {basename(row.path)}
                              </span>
                              <span className="text-muted-foreground">
                                {bytes(row.bytes)}
                                <ChevronRight className="ml-1 inline size-3" />
                              </span>
                            </div>
                            <div className="bar-track">
                              <i
                                style={{
                                  width: `${Math.max(1, (100 * row.bytes) / (overview.breakdown[0]?.bytes || 1))}%`,
                                  background:
                                    chartColors[i % chartColors.length],
                                }}
                              />
                            </div>
                          </button>
                        ))
                      ) : (
                        <p className="py-8 text-sm text-muted-foreground">
                          Run a scan to see the breakdown.
                        </p>
                      )}
                    </div>
                  </section>
                </div>
                <section>
                  <div className="section-heading">
                    <div>
                      <h2>Find your next cleanup</h2>
                      <p>Start with rebuildable files. Keep what matters.</p>
                    </div>
                    <span className="text-[11px] text-muted-foreground">
                      Nothing is selected automatically
                    </span>
                  </div>
                  <div className="recommendation-grid">
                    <Recommendation
                      title="Package & browser caches"
                      description="Downloaded packages and browser resources. Keep logins and saved data intact."
                      meta={`${number(counts.caches)} recognized cache folders`}
                      icon={<Database className="size-4" />}
                      onClick={() => navigate("caches")}
                    />
                    <Recommendation
                      title="Generated build output"
                      description="Review compiled builds, framework output and generated project artifacts."
                      meta={`${number(counts.generated)} folder-name matches`}
                      icon={<Box className="size-4" />}
                      onClick={() => navigate("generated")}
                    />
                    <Recommendation
                      title="Project dependencies"
                      description="Find node_modules, vendor and environments. Separate projects from installed apps."
                      meta={`${number(counts.dependencies)} folders, including nested`}
                      icon={<Package className="size-4" />}
                      onClick={() => navigate("dependencies")}
                    />
                  </div>
                </section>
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Worth a closer look</h2>
                      <p>
                        Largest recommended candidates. Review before removing.
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate("caches")}
                    >
                      View inventory
                      <ArrowRight className="size-3.5" />
                    </Button>
                  </div>
                  <div className="divide-y">
                    {overview?.recommendations.map((row) => (
                      <button
                        key={row.id}
                        onClick={() => inspect(row)}
                        className="suggestion-row"
                      >
                        <span className="grid size-9 shrink-0 place-items-center rounded-lg border bg-muted/40">
                          <Folder className="size-4" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <strong className="block truncate text-sm font-medium">
                            {basename(row.path)}
                          </strong>
                          <span className="mt-1 block truncate text-[11px] text-muted-foreground">
                            {row.path}
                          </span>
                        </span>
                        <Badge
                          variant="secondary"
                          className="hidden text-[10px] sm:inline-flex"
                        >
                          {row.category}
                        </Badge>
                        <span className="ml-3 shrink-0 text-sm font-medium tabular-nums">
                          {bytes(row.bytes)}
                        </span>
                        <ChevronRight className="size-4 text-muted-foreground" />
                      </button>
                    ))}
                  </div>
                  {!snapshot && (
                    <Empty
                      title="Your inventory starts with a scan"
                      description="Choose your drive or a specific folder. Flux reads metadata, not file contents."
                      action={
                        <Button onClick={() => setScanOpen(true)}>
                          Start first scan
                        </Button>
                      }
                    />
                  )}
                </section>
              </div>
            )}

            {tableView && (
              <section className="panel inventory-panel">
                <div className="inventory-top">
                  <div>
                    <h2>
                      {view === "tree"
                        ? "Folder contents"
                        : view === "large"
                          ? "Largest files"
                          : "Storage inventory"}
                    </h2>
                    <p>
                      {number(listing.total)} matching items · selecting an item
                      never deletes it
                    </p>
                  </div>
                  <div className="mode-switch" aria-label="Cleanup mode">
                    <button
                      aria-pressed={mode === "recommended"}
                      onClick={() => changeMode("recommended")}
                      className={cn(mode === "recommended" && "active")}
                    >
                      <ShieldCheck className="size-3.5" />
                      Recommended
                    </button>
                    <button
                      aria-pressed={mode === "advanced"}
                      onClick={() => changeMode("advanced")}
                      className={cn(mode === "advanced" && "active")}
                    >
                      <SlidersHorizontal className="size-3.5" />
                      Advanced
                    </button>
                    <button
                      aria-pressed={mode === "full"}
                      onClick={requestFullControl}
                      className={cn(mode === "full" && "active full-active")}
                      data-testid="full-control-mode"
                    >
                      <LockKeyhole className="size-3.5" />
                      Full control · risky
                    </button>
                  </div>
                </div>
                {mode === "recommended" && (
                  <div className="selection-help">
                    <Info className="size-4 shrink-0" />
                    <span>
                      You can select <b>any item</b> for review. Recommended
                      mode only permits recognized cleanup targets. To remove
                      ordinary files or folders, enable{" "}
                      <b>Full control · risky</b>.
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={requestFullControl}
                    >
                      Enable full control
                    </Button>
                  </div>
                )}
                {mode === "full" && (
                  <div className="mx-5 mb-4">
                    <ApprovalCard advanced>
                      <b>FULL CONTROL IS ARMED.</b> Credentials, signing keys,
                      browser profiles, application data and source folders can
                      be selected for permanent deletion. Every descendant is
                      listed in the live deletion manifest. Critical
                      OS/running-app locations and incompletely inventoried
                      linked trees remain blocked.{" "}
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-3"
                        onClick={() =>
                          api("/api/full-control", { enabled: false })
                            .then(() => {
                              changeMode("recommended");
                              refresh();
                            })
                            .catch((e) => notify(e.message))
                        }
                      >
                        Lock full control
                      </Button>
                    </ApprovalCard>
                  </div>
                )}
                {mode === "advanced" && (
                  <div className="mx-5 mb-4">
                    <ApprovalCard advanced>
                      Advanced mode enables manual deletion of ordinary scanned
                      files and folders—not just caches. These items may contain
                      irreplaceable data. Windows-critical locations, credential
                      stores and links remain protected.{" "}
                      <b>Enabling this mode does not delete anything.</b>
                    </ApprovalCard>
                  </div>
                )}
                {view === "tree" && (
                  <>
                    <ExplorerNavigation
                      folder={listing.folder}
                      ancestors={listing.ancestors || []}
                      onNavigate={browse}
                      onResolve={resolvePath}
                      onBack={() => goHistory(-1)}
                      onForward={() => goHistory(1)}
                      canBack={historyPosition > 0}
                      canForward={
                        historyPosition < folderHistory.current.length - 1
                      }
                    />
                    <div className="explorer-view-tools">
                      <Button
                        variant={showTree ? "secondary" : "ghost"}
                        size="sm"
                        onClick={() => setShowTree(!showTree)}
                        aria-pressed={showTree}
                      >
                        <PanelLeft className="size-3.5" />
                        Folder tree
                      </Button>
                      <span className="ml-auto hidden text-[10px] text-muted-foreground sm:inline">
                        Double-click icons to open folders · use checkboxes to
                        select
                      </span>
                      <div className="flex rounded-md border p-0.5">
                        <Button
                          variant={layout === "list" ? "secondary" : "ghost"}
                          size="icon-xs"
                          onClick={() => setLayout("list")}
                          aria-label="List view"
                          aria-pressed={layout === "list"}
                        >
                          <List className="size-3.5" />
                        </Button>
                        <Button
                          variant={layout === "grid" ? "secondary" : "ghost"}
                          size="icon-xs"
                          onClick={() => setLayout("grid")}
                          aria-label="Icon view"
                          aria-pressed={layout === "grid"}
                        >
                          <LayoutGrid className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                  </>
                )}
                <div className="inventory-tools">
                  <div className="search-input">
                    <Search className="size-4 text-muted-foreground" />
                    <Input
                      ref={searchRef}
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Search names or paths…"
                      aria-label="Search inventory"
                      className="border-0 bg-transparent shadow-none focus-visible:ring-0"
                    />
                    <kbd>Ctrl K</kbd>
                  </div>
                  <FilterChips
                    value={filter}
                    onChange={(v) => {
                      setFilter(v);
                      setOffset(0);
                    }}
                    items={[
                      { key: "all", label: "All items" },
                      { key: "eligible", label: "Recommended cleanup" },
                    ]}
                  />
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline" size="sm">
                        <SlidersHorizontal className="size-3.5" />
                        Filters
                        {(nested || old) && (
                          <span className="size-1.5 rounded-full bg-chart-3" />
                        )}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onSelect={(e) => {
                          e.preventDefault();
                          setNested(!nested);
                          setOffset(0);
                        }}
                      >
                        <span className="grid size-4 place-items-center rounded border">
                          {nested && <Check className="size-3" />}
                        </span>
                        Include nested dependencies
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onSelect={(e) => {
                          e.preventDefault();
                          setOld(!old);
                          setOffset(0);
                        }}
                      >
                        <span className="grid size-4 place-items-center rounded border">
                          {old && <Check className="size-3" />}
                        </span>
                        No modification in 90 days
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <div
                  className={cn(
                    "explorer-workspace",
                    view === "tree" && showTree && "with-folder-tree",
                  )}
                >
                  {view === "tree" && showTree && snapshot && (
                    <FolderTree
                      snapshotId={snapshot.id}
                      current={listing.folder?.id || parent}
                      ancestors={listing.ancestors || []}
                      onNavigate={browse}
                    />
                  )}
                  <div className="explorer-surface">
                    {listError ? (
                      <Empty
                        title="Couldn’t load this location"
                        description={listError}
                        action={
                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              onClick={() => {
                                setParent("");
                                setReload((n) => n + 1);
                              }}
                            >
                              Back to root
                            </Button>
                            <Button onClick={() => setReload((n) => n + 1)}>
                              Retry
                            </Button>
                          </div>
                        }
                      />
                    ) : (
                      <>
                        {view === "tree" && layout === "grid" ? (
                          <ExplorerGrid
                            rows={listing.rows}
                            selected={selected}
                            canSelect={canSelect}
                            onSelect={toggle}
                            onBrowse={browse}
                            onInspect={inspect}
                            loading={loading}
                          />
                        ) : (
                          <div
                            className={cn(
                              "inventory-scroll",
                              loading && "is-loading",
                            )}
                          >
                            <table>
                              <thead>
                                <tr>
                                  <th className="w-12">
                                    <Checkbox
                                      aria-label="Select items on this page"
                                      checked={allChecked}
                                      disabled={
                                        !!busy || loading || !allPage.length
                                      }
                                      onCheckedChange={(checked) => {
                                        setSelected((previous) => {
                                          const next = new Map(previous);
                                          allPage.forEach((row) => {
                                            if (checked && next.size < 500)
                                              next.set(row.id, row);
                                            else if (!checked)
                                              next.delete(row.id);
                                          });
                                          return next;
                                        });
                                      }}
                                    />
                                  </th>
                                  <th>
                                    <button onClick={() => sortBy("path")}>
                                      Name & location
                                      <ArrowUpDown className="size-3" />
                                    </button>
                                  </th>
                                  <th className="w-28">
                                    <button onClick={() => sortBy("bytes")}>
                                      Size
                                      {sort === "bytes" ? (
                                        <ArrowDown
                                          className={cn(
                                            "size-3",
                                            direction === "asc" && "rotate-180",
                                          )}
                                        />
                                      ) : (
                                        <ArrowUpDown className="size-3" />
                                      )}
                                    </button>
                                  </th>
                                  <th className="w-40">Classification</th>
                                  <th className="w-32">
                                    <button onClick={() => sortBy("newest")}>
                                      Modified*
                                      <ArrowUpDown className="size-3" />
                                    </button>
                                  </th>
                                  <th className="w-14" />
                                </tr>
                              </thead>
                              <tbody>
                                {loading && !listing.rows.length
                                  ? Array.from({ length: 6 }, (_, i) => (
                                      <tr key={i}>
                                        <td colSpan={6}>
                                          <Skeleton className="h-10 w-full" />
                                        </td>
                                      </tr>
                                    ))
                                  : listing.rows.map((row) => (
                                      <tr
                                        key={row.id}
                                        data-testid="inventory-row"
                                        className={cn(
                                          selected.has(row.id) &&
                                            "row-selected",
                                        )}
                                      >
                                        <td>
                                          <Tooltip>
                                            <TooltipTrigger asChild>
                                              <span className="inline-flex">
                                                <Checkbox
                                                  aria-label={`Select ${basename(row.path)}`}
                                                  checked={selected.has(row.id)}
                                                  disabled={
                                                    !canSelect(row) || loading
                                                  }
                                                  onCheckedChange={(checked) =>
                                                    toggle(row, !!checked)
                                                  }
                                                />
                                              </span>
                                            </TooltipTrigger>
                                            <TooltipContent className="max-w-80 text-xs">
                                              {canSelect(row)
                                                ? "Add to cleanup review"
                                                : status?.needs_rescan
                                                  ? "Rescan after cleanup first"
                                                  : busy
                                                    ? "Wait for the operation to finish"
                                                    : row.action_reason ||
                                                      "Inspect this item for available actions"}
                                            </TooltipContent>
                                          </Tooltip>
                                        </td>
                                        <td>
                                          <div className="flex min-w-0 items-start gap-3">
                                            <span
                                              className={cn(
                                                "file-icon",
                                                row.is_file && "file-type",
                                              )}
                                            >
                                              {row.is_file ? (
                                                <File className="size-4" />
                                              ) : (
                                                <Folder className="size-4" />
                                              )}
                                            </span>
                                            <div className="min-w-0 flex-1">
                                              <button
                                                className="item-name"
                                                onClick={() => inspect(row)}
                                              >
                                                {basename(row.path)}
                                              </button>
                                              <p
                                                className="item-path"
                                                title={row.path}
                                              >
                                                {row.path}
                                              </p>
                                            </div>
                                            {!row.is_file && (
                                              <Button
                                                variant="ghost"
                                                size="icon-xs"
                                                onClick={() => browse(row)}
                                                aria-label={`Browse ${basename(row.path)}`}
                                              >
                                                <ChevronRight className="size-3.5" />
                                              </Button>
                                            )}
                                          </div>
                                        </td>
                                        <td>
                                          <span className="text-sm font-medium tabular-nums">
                                            {bytes(row.bytes)}
                                          </span>
                                          <span className="mt-1 block text-[10px] text-muted-foreground">
                                            {row.files !== undefined
                                              ? number(row.files) +
                                                (row.is_file
                                                  ? " file"
                                                  : " files")
                                              : ""}
                                          </span>
                                        </td>
                                        <td>
                                          <Badge
                                            variant="outline"
                                            className={cn(
                                              "classification",
                                              row.risk === "safe" &&
                                                "border-chart-3/20 bg-chart-1/10 text-foreground",
                                            )}
                                          >
                                            {row.risk === "safe"
                                              ? "Rebuildable cache"
                                              : row.category}
                                          </Badge>
                                          {row.nested && (
                                            <span className="mt-1 block text-[10px] text-muted-foreground">
                                              Nested / bundled
                                            </span>
                                          )}
                                        </td>
                                        <td className="text-xs text-muted-foreground">
                                          {date(row.newest)}
                                        </td>
                                        <td>
                                          <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                              <Button
                                                variant="ghost"
                                                size="icon-xs"
                                                aria-label={`Actions for ${basename(row.path)}`}
                                              >
                                                <Ellipsis className="size-4" />
                                              </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end">
                                              <DropdownMenuItem
                                                onClick={() => inspect(row)}
                                              >
                                                <Info />
                                                Inspect item
                                              </DropdownMenuItem>
                                              {!row.is_file && (
                                                <DropdownMenuItem
                                                  onClick={() => browse(row)}
                                                >
                                                  <FolderOpen />
                                                  Browse contents
                                                </DropdownMenuItem>
                                              )}
                                              <DropdownMenuItem
                                                onClick={() => reveal(row)}
                                              >
                                                <ExternalLink />
                                                Show in File Explorer
                                              </DropdownMenuItem>
                                              <DropdownMenuItem
                                                onClick={() => copy(row.path)}
                                              >
                                                Copy full path
                                              </DropdownMenuItem>
                                              <DropdownMenuSeparator />
                                              <DropdownMenuItem
                                                disabled={!canSelect(row)}
                                                onClick={() =>
                                                  toggle(
                                                    row,
                                                    !selected.has(row.id),
                                                  )
                                                }
                                              >
                                                <Trash2 />
                                                {selected.has(row.id)
                                                  ? "Remove from selection"
                                                  : "Add to cleanup review"}
                                              </DropdownMenuItem>
                                            </DropdownMenuContent>
                                          </DropdownMenu>
                                        </td>
                                      </tr>
                                    ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                        {!loading && !listing.rows.length && (
                          <Empty
                            title={
                              snapshot
                                ? "No matching items"
                                : "No inventory yet"
                            }
                            description={
                              snapshot
                                ? "Try a different path or filter. Nested folders are hidden by default."
                                : "Start a scan to explore this computer."
                            }
                            action={
                              snapshot ? (
                                <Button
                                  variant="outline"
                                  onClick={() => {
                                    setQuery("");
                                    setFilter("all");
                                    setOld(false);
                                  }}
                                >
                                  Clear filters
                                </Button>
                              ) : (
                                <Button onClick={() => setScanOpen(true)}>
                                  Start scan
                                </Button>
                              )
                            }
                          />
                        )}
                        <div className="table-pagination">
                          <span>
                            {loading ? (
                              <span className="flex items-center gap-2">
                                <LoaderCircle className="size-3 animate-spin" />
                                Loading inventory…
                              </span>
                            ) : listing.total ? (
                              `${number(offset + 1)}–${number(Math.min(offset + 50, listing.total))} of ${number(listing.total)}`
                            ) : (
                              "0 items"
                            )}
                            {selected.size > 0 && (
                              <span className="ml-3 text-foreground">
                                {selected.size} selected
                              </span>
                            )}
                          </span>
                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={!offset || loading}
                              onClick={() =>
                                setOffset(Math.max(0, offset - 50))
                              }
                            >
                              <ArrowLeft className="size-3.5" />
                              Previous
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={offset + 50 >= listing.total || loading}
                              onClick={() => setOffset(offset + 50)}
                            >
                              Next
                              <ArrowRight className="size-3.5" />
                            </Button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </section>
            )}

            {view === "activity" && (
              <section className="panel p-5">
                <div className="section-heading">
                  <div>
                    <h2>Recent operations</h2>
                    <p>Actual results, not simulated progress.</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setReload((n) => n + 1)}
                  >
                    <RefreshCw className="size-3.5" />
                    Refresh
                  </Button>
                </div>
                <div className="space-y-2">
                  {events.map((event, i) => (
                    <TaskRow
                      key={String(event.at) + i}
                      title={
                        event.kind === "maintenance"
                          ? "Approved system maintenance"
                          : event.kind === "cleanup"
                            ? "Confirmed cleanup"
                            : "Storage scan"
                      }
                      meta={new Date(event.at * 1000).toLocaleString()}
                      status={
                        event.status === "error" ||
                        (Array.isArray(event.results) &&
                          event.results.some((r: any) => r.status === "error"))
                          ? "error"
                          : "done"
                      }
                    >
                      <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed">
                        {JSON.stringify(event, null, 2)}
                      </pre>
                    </TaskRow>
                  ))}
                </div>
                {!events.length && (
                  <Empty
                    title="A clean slate"
                    description="Completed scans and cleanup results will appear here."
                  />
                )}
              </section>
            )}
            {view === "issues" && (
              <section className="panel p-5">
                <ApprovalCard>
                  Flux is{" "}
                  {status?.is_admin
                    ? "running as administrator"
                    : "not elevated"}
                  . Some Windows-protected locations still deny access. Links
                  and cloud placeholders are deliberately not followed. The app
                  will not take ownership of Windows files or change their
                  security permissions.
                </ApprovalCard>
                <div className="my-5 flex flex-wrap gap-3">
                  <Badge variant="outline">
                    {number(snapshot?.error_count)} read errors recorded
                  </Badge>
                  <Badge variant="outline">
                    {number(snapshot?.skipped_links)} links / placeholders
                    skipped
                  </Badge>
                </div>
                <div className="space-y-2">
                  {issues.map((issue, i) => (
                    <TaskRow
                      key={issue.path + i}
                      title={issue.path}
                      status="error"
                      meta="Not read"
                    >
                      <p className="break-all font-mono text-xs">
                        {issue.error}
                      </p>
                    </TaskRow>
                  ))}
                </div>
                {!issues.length && (
                  <Empty
                    title="No read errors recorded"
                    description="A scan is still needed to verify all selected locations."
                  />
                )}
              </section>
            )}

            <footer className="page-footer">
              <span>
                <ShieldCheck className="size-3" />
                Local, private, approval-first.
              </span>
              <p>
                *Modification time is not last use. Folder sizes overlap and are
                not guaranteed recoverable space.
              </p>
              <span>Flux Storage {status?.version} · MTR Soft</span>
            </footer>
          </main>
        </div>

        {selected.size > 0 && (
          <div className="selection-dock">
            <div className="grid size-9 place-items-center rounded-lg bg-primary text-primary-foreground">
              <Check className="size-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">
                {selected.size} item{selected.size === 1 ? "" : "s"} selected
              </p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">
                {mode === "full"
                  ? "Risky full-control selections"
                  : mode === "advanced" ? "Manual selections" : "Selections · Recommended mode"}{" "}
                · exact live size in preview
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelected(new Map())}
            >
              Clear
            </Button>
            <Button
              disabled={!!busy || !!offline}
              onClick={() => prepare()}
              data-testid="review-cleanup"
            >
              Review cleanup
              <ArrowRight className="size-3.5" />
            </Button>
          </div>
        )}

        <Sheet
          open={!!detail}
          onOpenChange={(open) => {
            if (!open) setDetail(null);
          }}
        >
          <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
            <SheetHeader>
              <SheetTitle className="pr-8 break-all">
                {detail ? basename(detail.path) : "Item details"}
              </SheetTitle>
              <SheetDescription>
                Inspect the location and consequences before taking action.
              </SheetDescription>
            </SheetHeader>
            {detail && (
              <div className="space-y-5 p-6 pt-2">
                <PathBlock
                  path={detail.path}
                  onCopy={() => copy(detail.path)}
                />
                <div className="grid grid-cols-2 gap-3">
                  <div className="detail-metric">
                    <span>Logical size</span>
                    <strong>{bytes(detail.bytes)}</strong>
                  </div>
                  <div className="detail-metric">
                    <span>Files</span>
                    <strong>{number(detail.files)}</strong>
                  </div>
                  <div className="detail-metric">
                    <span>Classification</span>
                    <strong className="text-sm!">{detail.category}</strong>
                  </div>
                  <div className="detail-metric">
                    <span>Newest modification</span>
                    <strong className="text-sm!">{date(detail.newest)}</strong>
                  </div>
                </div>
                <ApprovalCard
                  advanced={mode === "advanced" && detail.delete_allowed}
                >
                  {detail.action_reason || detail.reason}
                  {detail.links
                    ? ` ${number(detail.links)} links/junctions were skipped inside this folder.`
                    : ""}
                </ApprovalCard>
                {detail.exists === false && (
                  <p className="text-sm text-destructive">
                    This item no longer exists. Run a fresh scan.
                  </p>
                )}
                <div className="space-y-2">
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => reveal(detail)}
                  >
                    <ExternalLink />
                    Show in File Explorer
                  </Button>
                  {!detail.is_file && (
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => browse(detail)}
                    >
                      <FolderOpen />
                      Browse folder contents
                    </Button>
                  )}
                  <Button
                    className="w-full"
                    disabled={!canSelect(detail) || detail.exists === false}
                    onClick={() => {
                      toggle(detail, true);
                      setDetail(null);
                    }}
                  >
                    <Trash2 />
                    Add to cleanup review
                  </Button>
                  {!detail.delete_allowed && mode === "recommended" && (
                    <Button
                      variant="ghost"
                      className="w-full"
                      onClick={() => {
                        changeMode("advanced");
                        notify(
                          "Advanced manual mode is enabled. Inspect the item again to see available actions.",
                        );
                      }}
                    >
                      <SlidersHorizontal />
                      Switch to advanced manual mode
                    </Button>
                  )}
                  {detail.category === "System / installed apps" && (
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() =>
                        api("/api/windows-apps", {}).catch((e) =>
                          notify(e.message),
                        )
                      }
                    >
                      Open Windows app management
                    </Button>
                  )}
                </div>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Modification dates do not prove a folder is unused. Project
                  dependencies must be reinstalled after removal, and local
                  edits inside them may be lost.
                </p>
              </div>
            )}
          </SheetContent>
        </Sheet>

        <Dialog open={scanOpen} onOpenChange={setScanOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Take a fresh look.</DialogTitle>
              <DialogDescription>
                Scan a drive or any existing local folder. No file contents are
                read or uploaded.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <label className="block text-xs font-medium">
                Quick location
                <Select
                  value={status?.roots.includes(scanRoot) ? scanRoot : ""}
                  onValueChange={setScanRoot}
                >
                  <SelectTrigger className="mt-2 w-full">
                    <SelectValue placeholder="Choose a location" />
                  </SelectTrigger>
                  <SelectContent>
                    {status?.roots.map((root) => (
                      <SelectItem key={root} value={root}>
                        {root}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </label>
              <label className="block text-xs font-medium" htmlFor="scan-path">
                Or enter a local path
                <Input
                  id="scan-path"
                  value={scanRoot}
                  onChange={(e) => setScanRoot(e.target.value)}
                  className="mt-2 font-mono text-xs"
                  placeholder="Absolute local folder or drive path"
                />
              </label>
              <ApprovalCard>
                {status?.is_admin
                  ? "Administrator privileges are active."
                  : "Start through the desktop shortcut and approve UAC to scan as administrator."}{" "}
                Junctions and inaccessible Windows-protected locations will
                still be skipped and reported.
              </ApprovalCard>
              <Button
                className="w-full"
                onClick={startScan}
                disabled={actionBusy || !scanRoot.trim() || !!busy}
              >
                {actionBusy ? (
                  <LoaderCircle className="animate-spin" />
                ) : (
                  <Play />
                )}
                Start scan
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        <Dialog
          open={previewOpen}
          onOpenChange={(open) => {
            if (!actionBusy) setPreviewOpen(open);
          }}
        >
          <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-3xl">
            <DialogHeader>
              <DialogTitle>Review your cleanup.</DialogTitle>
              <DialogDescription>
                Only these exact selections will be removed. This is permanent
                deletion, not the Recycle Bin.
              </DialogDescription>
            </DialogHeader>
            {previewBusy ? (
              <div className="py-8">
                <LoadingState label="Verifying current files and paths" />
                <p className="mt-3 text-xs text-muted-foreground">
                  Large caches can take a little time. No deletion is happening.
                </p>
              </div>
            ) : (
              preview && (
                <div className="space-y-4">
                  {preview.blocked.length>0&&<div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-xs"><strong className="block text-sm">{preview.blocked.length} selections are blocked in this mode. Nothing has been deleted.</strong><div className="my-3 max-h-36 space-y-3 overflow-auto">{preview.blocked.map(row=><div key={row.id}><code className="block break-all">{row.path}</code><p className="mt-1 text-muted-foreground">{row.action_reason}</p></div>)}</div><div className="flex flex-wrap gap-2"><Button variant="outline" size="sm" onClick={removeBlocked}>Remove blocked selections</Button>{mode!=='full'&&<Button variant="outline" size="sm" onClick={()=>{setPreviewOpen(false);requestFullControl()}}>Enable full control instead</Button>}</div></div>}
                  <div className="max-h-56 divide-y overflow-y-auto rounded-lg border">
                    {preview.rows.map((row) => (
                      <div key={row.id} className="p-3">
                        <div className="mb-1 flex items-center justify-between text-xs">
                          <span className="font-medium">
                            {basename(row.path)}
                          </span>
                          <span className="tabular-nums">
                            {bytes(row.bytes)}
                          </span>
                        </div>
                        <code className="block break-all text-[10px] text-muted-foreground">
                          {row.path}
                        </code>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span>
                      {preview.rows.length} exact targets · overlaps removed
                    </span>
                    <strong>{bytes(preview.bytes)} live logical size</strong>
                  </div>
                  {preview.rows.length>0&&<DeletionManifest ticket={preview.ticket} summary={preview.manifest}/>}
                  <ApprovalCard advanced={preview.mode !== "recommended"}>
                    {preview.mode !== "recommended"
                      ? "These are manual selections and may contain your only copy of source code, databases, app data or histories. Nothing here is guaranteed disposable."
                      : "Close related apps, stop builds and package installs first. Caches will be downloaded again; dependencies must be reinstalled. Any custom edits inside selected folders will be lost."}{" "}
                    Actual freed space can be lower because of hardlinks.
                  </ApprovalCard>
                  {preview.mode !== "recommended" && (
                    <label className="flex items-start gap-3 text-xs leading-relaxed">
                      <Checkbox
                        checked={ack}
                        onCheckedChange={(value) => setAck(!!value)}
                        className="mt-0.5"
                      />
                      I understand that these manual selections may contain
                      irreplaceable data and accept permanent deletion.
                    </label>
                  )}
                  <label
                    htmlFor="delete-confirmation"
                    className="block text-xs font-medium"
                  >
                    Type DELETE to confirm permanent removal
                    <Input
                      id="delete-confirmation"
                      value={confirmation}
                      onChange={(e) => setConfirmation(e.target.value)}
                      placeholder="DELETE"
                      autoComplete="off"
                      className="mt-2 font-mono"
                    />
                  </label>
                  <Button
                    variant="destructive"
                    className="w-full"
                    disabled={
                      confirmation !== "DELETE" ||
                      (preview.mode !== "recommended" && !ack) ||
                      preview.blocked.length>0 || !preview.rows.length ||
                      actionBusy ||
                      Date.now() / 1000 > preview.expires
                    }
                    onClick={cleanup}
                    data-testid="confirm-delete"
                  >
                    {actionBusy ? (
                      <LoaderCircle className="animate-spin" />
                    ) : (
                      <Trash2 />
                    )}
                    Permanently delete selected items
                  </Button>
                  <p className="text-center text-[10px] text-muted-foreground">
                    Preview expires in 5 minutes. Changed targets are rejected
                    before removal.
                  </p>
                </div>
              )
            )}
            {previewError && (
              <div
                role="alert"
                className="rounded-lg border border-destructive/25 bg-destructive/5 p-3 text-xs leading-relaxed text-destructive"
              >
                {previewError}
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3 w-full"
                  onClick={() => prepare()}
                >
                  Refresh live preview
                </Button>
              </div>
            )}
          </DialogContent>
        </Dialog>
        <Dialog open={unlockOpen} onOpenChange={setUnlockOpen}><DialogContent className="sm:max-w-xl"><DialogHeader><DialogTitle>Enable risky full control?</DialogTitle><DialogDescription>This unlocks data-policy restrictions, not Windows security permissions. No files are deleted by enabling it.</DialogDescription></DialogHeader><ApprovalCard advanced>You can permanently remove ordinary files, whole user folders, credentials, signing keys, browser profiles, databases and source. This may destroy your only copy or break applications. The running OS/app and linked or incompletely inventoried trees remain protected. This permission expires when the server restarts.</ApprovalCard><label className="flex items-start gap-3 text-xs leading-relaxed"><Checkbox checked={unlockAck} onCheckedChange={value=>setUnlockAck(!!value)}/>I understand the risks and want full control over my data selections.</label><label htmlFor="full-control-confirmation" className="text-xs font-medium">Type ENABLE FULL CONTROL<Input id="full-control-confirmation" value={unlockText} onChange={event=>setUnlockText(event.target.value)} autoComplete="off" className="mt-2 font-mono"/></label><Button variant="destructive" disabled={!unlockAck||unlockText!=='ENABLE FULL CONTROL'||actionBusy||!status?.is_admin} onClick={unlock} data-testid="unlock-full-control">{actionBusy?<LoaderCircle className="animate-spin"/>:<LockKeyhole/>}Enable full control</Button></DialogContent></Dialog>
        {toast && (
          <div className="toast" role="status">
            <Info className="size-4 shrink-0" />
            <span>{toast}</span>
            <button
              onClick={() => setToast("")}
              aria-label="Dismiss notification"
            >
              <X className="size-3.5" />
            </button>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}

function Empty({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="mb-4 grid size-12 place-items-center rounded-xl border bg-muted/40">
        <Search className="size-5 text-muted-foreground" />
      </div>
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 max-w-md text-xs leading-relaxed text-muted-foreground">
        {description}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
