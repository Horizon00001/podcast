import { createBrowserRouter } from 'react-router-dom'
import App from '../App'
import { GeneratePage } from '../pages/GeneratePage'
import { PodcastDetailPage } from '../pages/PodcastDetailPage'
import { PodcastListPage } from '../pages/PodcastListPage'
import { SubscriptionPage } from '../pages/SubscriptionPage'
import { SettingsPage } from '../pages/SettingsPage'

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <PodcastListPage /> },
      { path: "podcasts/:id", element: <PodcastDetailPage /> },
      { path: "generate", element: <GeneratePage /> },
      { path: "subscriptions", element: <SubscriptionPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
])