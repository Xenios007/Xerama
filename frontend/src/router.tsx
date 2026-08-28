import { createBrowserRouter, type RouteObject } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { ProjectDetailPage } from "./pages/ProjectDetailPage";
import { StoryStudioPage } from "./pages/StoryStudioPage";
import { CharacterStudioPage } from "./pages/CharacterStudioPage";
import { CharacterDetailPage } from "./pages/CharacterDetailPage";
import { ProductionStudioPage } from "./pages/ProductionStudioPage";
import { ReviewApprovalStudioPage } from "./pages/ReviewApprovalStudioPage";
import { SettingsPage } from "./pages/SettingsPage";
import { LibraryPage } from "./pages/LibraryPage";

// Exported separately from the router itself so tests can build a
// MemoryRouter from the exact same route tree instead of duplicating it.
//
// Note: `/story`, `/characters`, `/production`, `/review` without an ID
// used to render a dead-end placeholder ("go back to the Dashboard") -
// removed in favor of the contextual links already on `ProjectDetailPage`
// (into `/story/:seriesId` etc.), which is the only place those IDs come
// from anyway.
export const routes: RouteObject[] = [
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "projects/:projectId", element: <ProjectDetailPage /> },
      { path: "story/:seriesId", element: <StoryStudioPage /> },
      { path: "characters/:seriesId", element: <CharacterStudioPage /> },
      { path: "characters/:seriesId/:characterId", element: <CharacterDetailPage /> },
      { path: "production/:episodeId", element: <ProductionStudioPage /> },
      { path: "review/:projectId", element: <ReviewApprovalStudioPage /> },
      { path: "library/:projectId", element: <LibraryPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
