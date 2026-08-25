import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { QueryState } from "../components/ui/QueryState";
import { useArchiveProject, useCreateProject, useProjects } from "../api/queries";
import "./DashboardPage.css";

export function DashboardPage() {
  const { data: projects, isLoading, error } = useProjects();
  const createProject = useCreateProject();
  const archiveProject = useArchiveProject();
  const [name, setName] = useState("");

  function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    createProject.mutate({ name: name.trim() }, { onSuccess: () => setName("") });
  }

  const active = (projects ?? []).filter((p) => p.status !== "archived");
  const archived = (projects ?? []).filter((p) => p.status === "archived");

  return (
    <div>
      <h1>Project Dashboard</h1>
      <Card title="New project">
        <form onSubmit={handleCreate} className="xr-dashboard__create-form">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Project name"
            aria-label="Project name"
          />
          <Button type="submit" disabled={createProject.isPending || !name.trim()}>
            Create
          </Button>
        </form>
      </Card>

      <div className="xr-dashboard__section">
        <QueryState isLoading={isLoading} error={error}>
          {active.length === 0 && archived.length === 0 ? (
            <p>No projects yet - create one above.</p>
          ) : (
            <div className="xr-dashboard__grid">
              {active.map((project) => (
                <Card key={project.id}>
                  <div className="xr-dashboard__card-header">
                    <Link to={`/projects/${project.id}`}>
                      <strong>{project.name}</strong>
                    </Link>
                    <span className={`xr-badge xr-badge--${project.status}`}>{project.status}</span>
                  </div>
                  {project.description && <p className="xr-dashboard__desc">{project.description}</p>}
                  <p className="xr-dashboard__meta">
                    Created {new Date(project.created_at).toLocaleDateString()}
                  </p>
                  <Button
                    variant="secondary"
                    onClick={() => archiveProject.mutate(project.id)}
                    disabled={archiveProject.isPending}
                  >
                    Archive
                  </Button>
                </Card>
              ))}
            </div>
          )}
          {archived.length > 0 && (
            <details className="xr-dashboard__archived">
              <summary>{archived.length} archived project(s)</summary>
              <ul>
                {archived.map((project) => (
                  <li key={project.id}>
                    <Link to={`/projects/${project.id}`}>{project.name}</Link>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </QueryState>
      </div>
    </div>
  );
}
