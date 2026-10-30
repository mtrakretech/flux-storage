import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'
import { setNonce } from 'get-nonce'

setNonce(document.querySelector<HTMLMetaElement>('meta[name="csp-nonce"]')?.content || '')

class ErrorBoundary extends React.Component<{children:React.ReactNode},{error:string}> {
  state={error:''}
  static getDerivedStateFromError(error:Error){return {error:error.message}}
  render(){return this.state.error?<div className="m-auto max-w-lg p-12"><h1 className="mb-4 text-xl font-semibold">The interface couldn’t render.</h1><p className="mb-5 text-sm text-muted-foreground">Your files have not been changed. {this.state.error}</p><button className="rounded-md bg-primary px-4 py-2 text-primary-foreground" onClick={()=>location.reload()}>Reload Flux</button></div>:this.props.children}
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><ErrorBoundary><App/></ErrorBoundary></React.StrictMode>)
