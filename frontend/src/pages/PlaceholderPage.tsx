import { Card } from "../components/ui/Card";

export function PlaceholderPage({ title, module }: { title: string; module: string }) {
  return (
    <div>
      <h1>{title}</h1>
      <Card>
        <p>This studio page is built in {module}. The shell (routing, API client, design system) is ready to host it.</p>
      </Card>
    </div>
  );
}
