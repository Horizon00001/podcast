import { createBrowserRouter } from 'react-router-dom'

import App from '../App'
import { GeneratePage } from '../pages/GeneratePage'
import { PodcastDetailPage } from '../pages/PodcastDetailPage'
import { PodcastListPage } from '../pages/PodcastListPage'

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      {
        index: true,
        element: <PodcastListPage />,
      },
      {
        path: "podcasts/:id",
        element: <PodcastDetailPage />,
      },
      {
        path: "generate",
        element: <GeneratePage />,
      },
    ],
  },
])
