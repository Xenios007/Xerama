import { createBrowserRouter, type RouteObject } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { ProjectDetailPage } from "./pages/ProjectDetailPage";
import { StoryStudioPage } from "./pages/StoryStudioPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";

// Exported separately from the router itself so tests can build a
// MemoryRouter from the exact same route tree instead of duplicating it.
export const routes: RouteObject[] = [
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "projects/:projectId", element: <ProjectDetailPage /> },
      {
        path: "story",
        element: (
          <PlaceholderPage
            title="Story Studio"
            module="MODULE-057 - open a project's series from the Dashboard to view it"
          />
        ),
      },
      { path: "story/:seriesId", element: <StoryStudioPage /> },
      {
        path: "characters",
        element: <PlaceholderPage title="Character Studio" module="MODULE-058" />,
      },
      {
        path: "production",
        element: <PlaceholderPage title="Production Studio" module="MODULE-059" />,
      },
      {
        path: "review",
        element: <PlaceholderPage title="Review & Approval Studio" module="MODULE-060" />,
      },
    ],
  },
];

export const router = createBrowserRouter(routes);
