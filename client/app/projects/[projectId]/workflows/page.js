import WorkflowsView from "../../../../components/workflows/WorkflowsView";

export default async function WorkflowsPage({ params }) {
  const { projectId } = await params;
  return <WorkflowsView projectId={projectId} />;
}
