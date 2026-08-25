import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { QueryState } from "../components/ui/QueryState";
import { useCreateProject, useProjects } from "../api/queries";

export function DashboardPage() {
  const { data: projects, isLoading, error } = useProjects();
  const createProject = useCreateProject();
  const [name, setName] = useState("");

  function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    createProject.mutate({ name: name.trim() }, { onSuccess: () => setName("") });
  }

  return (
    <div>
      <h1>Project Dashboard</h1>
      <Card title="New project">
        <form onSubmit={handleCreate} style={{ display: "flex", gap: "0.5rem" }}>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Project name"
            aria-label="Project name"
          />
          <Button type="submit" disabled={createProject.isPending}>
            Create
          </Button>
        </form>
      </Card>

      <div style={{ marginTop: "1.5rem" }}>
        <Card title="Projects">
          <QueryState isLoading={isLoading} error={error}>
            {projects && projects.length > 0 ? (
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {projects.map((project) => (
                  <li key={project.id} style={{ padding: "0.5rem 0" }}>
                    <Link to={`/projects/${project.id}`}>{project.name}</Link>
                    <span style={{ marginLeft: "0.5rem", color: "var(--xr-color-muted, #6b7280)" }}>
                      {project.status}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No projects yet - create one above.</p>
            )}
          </QueryState>
        </Card>
      </div>
    </div>
  );
}
