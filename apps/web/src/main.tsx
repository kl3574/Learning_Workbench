import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Shell } from './workbench/Shell'
import './style.css'
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } })
createRoot(document.getElementById('root')!).render(<QueryClientProvider client={queryClient}><Shell /></QueryClientProvider>)
