/* @refresh reload */
import { render } from 'solid-js/web'
import { RouterProvider, createRouter } from '@tanstack/solid-router'
import { QueryClient, QueryClientProvider } from '@tanstack/solid-query'
import { routeTree } from './routeTree.gen'
import { configureApi } from './api/client'
import { auth, homePath } from './auth/store'
import { toast } from './components/toast'
import { t } from './i18n'
import '@unocss/reset/tailwind.css'
import 'virtual:uno.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
  },
})

export const router = createRouter({ routeTree })
declare module '@tanstack/solid-router' {
  interface Register {
    router: typeof router
  }
}

configureApi({
  getToken: () => auth.get().token,
  onUnauthorized: () => {
    if (auth.get().token) toast('error', t('sessionExpired'))
    auth.logout()
    router.navigate({ to: '/login' })
  },
})

const Root = () => (
  <QueryClientProvider client={queryClient}>
    <RouterProvider router={router} />
  </QueryClientProvider>
)

render(() => <Root />, document.getElementById('root')!)

// re-export for convenience
export { homePath }
