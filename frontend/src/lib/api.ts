export type Mode = 'recommended' | 'advanced' | 'full'
export type Item = { id:string; path:string; parent?:string; bytes:number; files?:number; newest:number; category:string; risk:string; eligible:boolean; delete_allowed?:boolean; action_reason?:string; reason?:string; nested?:boolean; is_file?:boolean; links?:number; exists?:boolean }
export type Job = { id?:string; kind:string; status:string; phase?:string; started?:number; elapsed?:number; files?:number; directories?:number; current?:string; completed?:number; total?:number; recovered_bytes?:number; error?:string; results?:unknown[] }
export type Drive = {id:string;path:string;label:string;type:string;filesystem?:string;status:string;ready:boolean;can_scan:boolean;read_only?:boolean;total:number;used:number;free:number;error?:string}
export type Preferences = {theme:'light'|'dark'|'system';preferred_port:number;open_browser:boolean}
export type Status = { app:string; publisher:string;version:string; is_admin:boolean; full_control_enabled:boolean; pid:number; disk:Drive;storage:{drives:Drive[];aggregate:{total:number;used:number;free:number};updated:number;error:string};preferences:Preferences;connection:{port:number;url:string;automatic:boolean}; needs_rescan:boolean; job:Job; roots:string[]; snapshot:null|{ id:string; root:string; scanned_at:number; file_count:number; directory_count:number; candidate_bytes:number; candidate_count:number; skipped_links:number; error_count:number; elapsed:number } }
export type Listing = {rows:Item[];total:number;folder?:Item;ancestors?:{id:string;path:string}[]}
export type Overview = { breakdown:Item[]; recommendations:Item[]; counts:Record<string,number> }
export type ManifestSummary = {files:number;folders:number;entries:number;bytes:number}
export type Preview = { ticket:string; expires:number; bytes:number; mode:Mode; rows:Item[];blocked:Item[];manifest:ManifestSummary }
export type Activity = { at:number; kind:string; [key:string]:unknown }

const token = () => document.querySelector<HTMLMetaElement>('meta[name="flux-token"]')?.content || ''
export async function api<T>(url:string,data?:unknown,signal?:AbortSignal):Promise<T> {
  const response = await fetch(url, {signal:signal||AbortSignal.timeout(120000), ...(data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Flux-Token':token()},body:JSON.stringify(data)})})
  if(response.status===403)throw new Error('This local session changed or is not authorized. Refresh the page (Ctrl+F5), then try again.')
  const type=response.headers.get('content-type')||''
  if(!type.includes('application/json')) throw new Error(`Server returned ${response.status}. Reload the page or restart Flux.`)
  const payload=await response.json()
  if(!response.ok) throw new Error(payload.error||`Request failed (${response.status}).`)
  return payload
}
export const bytes=(n?:number) => {
  if(n===undefined||!Number.isFinite(n))return '—'
  const abs=Math.abs(n), sign=n<0?'−':''
  for(const [unit,value] of [['TB',2**40],['GB',2**30],['MB',2**20],['KB',2**10]] as const) if(abs>=value)return sign+(abs/value).toLocaleString(undefined,{maximumFractionDigits:1})+' '+unit
  return sign+abs+' B'
}
export const number=(n?:number)=>new Intl.NumberFormat().format(n||0)
export const basename=(path:string)=>path.replace(/[\\/]+$/,'').split(/[\\/]/).pop()||path
export const date=(n?:number)=>n?new Date(n*1000).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'}):'Unknown'
