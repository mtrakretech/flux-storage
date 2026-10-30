/** Adapted from Beautiful UI's MIT-licensed Loading State, Task Rows, Filter Table,
 * Recommendation Card and Approval Card patterns. Copyright (c) 2026 Shane Levine.
 * See frontend/THIRD-PARTY-NOTICES.md. Demo sequences are replaced with real state. */
import { useEffect, useState, type ReactNode } from 'react'
import { Check, ChevronDown, ChevronRight, CircleAlert, Copy, Folder, LoaderCircle, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export function LoadingState({label='Reading metadata',started}:{label?:string;started?:number}) {
  const [elapsed,setElapsed]=useState(0)
  useEffect(()=>{const start=started?started*1000:Date.now(); const update=()=>setElapsed(Math.max(0,(Date.now()-start)/1000));update();const timer=setInterval(update,1000);return()=>clearInterval(timer)},[started])
  return <div role="status" className="flex items-center gap-3 text-sm"><span aria-hidden className="grid grid-cols-3 gap-[2px]">{Array.from({length:9},(_,i)=><span key={i} className="pixel-cell" style={{animationDelay:`${(i%3+Math.abs(Math.floor(i/3)-1))*90}ms`}}/>)}</span><span className="shimmer-label font-medium">{label}</span><span className="text-muted-foreground font-mono text-xs tabular-nums">{elapsed<60?`${Math.floor(elapsed)}s`:`${Math.floor(elapsed/60)}m ${Math.floor(elapsed%60)}s`}</span></div>
}

export function FilterChips({value,onChange,items}:{value:string;onChange:(key:string)=>void;items:{key:string;label:string;count?:number}[]}) {
  return <div className="flex gap-1 overflow-x-auto rounded-lg bg-muted/70 p-1" role="group" aria-label="Inventory filters">{items.map(item=><button key={item.key} aria-pressed={value===item.key} onClick={()=>onChange(item.key)} className={cn('flex shrink-0 items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition-all',value===item.key?'bg-background text-foreground shadow-sm':'text-muted-foreground hover:text-foreground')}>
    {item.label}{item.count!==undefined&&<span className="rounded bg-muted px-1.5 py-0.5 text-[10px] tabular-nums">{item.count}</span>}</button>)}</div>
}

export function TaskRow({title,meta,status='done',children}:{title:string;meta?:string;status?:'done'|'running'|'error';children:ReactNode}) {
  const [open,setOpen]=useState(false)
  return <div className="overflow-hidden rounded-lg border bg-card"><button onClick={()=>setOpen(!open)} aria-expanded={open} className="flex w-full items-center gap-3 p-3.5 text-left hover:bg-muted/50 transition-colors">
    <span className={cn('grid size-7 shrink-0 place-items-center rounded-full',status==='error'?'bg-destructive/10 text-destructive':status==='running'?'bg-muted':'bg-muted text-foreground')}>{status==='running'?<LoaderCircle className="size-3.5 animate-spin"/>:status==='error'?<CircleAlert className="size-3.5"/>:<Check className="size-3.5"/>}</span>
    <span className="min-w-0 flex-1 truncate text-sm font-medium">{title}</span><span className="hidden text-xs text-muted-foreground sm:block">{meta}</span><ChevronDown className={cn('size-4 shrink-0 text-muted-foreground transition-transform',open&&'rotate-180')}/></button>
    <div className="grid transition-[grid-template-rows,opacity] duration-200" style={{gridTemplateRows:open?'1fr':'0fr',opacity:open?1:0}}><div className="overflow-hidden"><div className="border-t bg-muted/25 p-4 text-xs text-muted-foreground">{children}</div></div></div>
  </div>
}

export function Recommendation({title,description,meta,onClick,icon}:{title:string;description:string;meta:string;onClick:()=>void;icon:ReactNode}) {
  return <button onClick={onClick} className="group flex min-w-0 flex-col rounded-xl border bg-card p-5 text-left shadow-xs transition-all hover:border-ring/50 hover:shadow-md active:scale-[.995]">
    <div className="mb-4 flex w-full items-center justify-between"><span className="grid size-9 place-items-center rounded-lg border bg-muted/50">{icon}</span><ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-1"/></div>
    <span className="text-sm font-semibold">{title}</span><span className="mt-1 text-xs leading-relaxed text-muted-foreground">{description}</span><span className="mt-4 text-xs font-medium">{meta}</span>
  </button>
}

export function ApprovalCard({children,advanced=false}:{children:ReactNode;advanced?:boolean}) {
  return <div className={cn('rounded-lg border p-4',advanced?'border-destructive/25 bg-destructive/5':'bg-muted/40')}><div className="mb-2 flex items-center gap-2 text-sm font-medium">{advanced?<CircleAlert className="size-4 text-destructive"/>:<ShieldCheck className="size-4"/>}{advanced?'Manual deletion · your responsibility':'Approval required'}</div><div className="text-xs leading-relaxed text-muted-foreground">{children}</div></div>
}

export function PathBlock({path,onCopy}:{path:string;onCopy:()=>void}) {
  return <div className="flex items-start gap-2 rounded-md border bg-muted/40 px-3 py-2.5"><Folder className="mt-0.5 size-3.5 shrink-0 text-muted-foreground"/><code className="min-w-0 flex-1 break-all text-xs leading-relaxed">{path}</code><Button variant="ghost" size="icon-xs" onClick={onCopy} aria-label="Copy path"><Copy className="size-3.5"/></Button></div>
}
