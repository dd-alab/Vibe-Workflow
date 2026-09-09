import WorkflowEditorClient from "../../../../../components/workflows/WorkflowEditorClient";

export default async function WorkflowEditorPage({ params }) {
  const { projectId, workflowId } = await params;
  return (
    <WorkflowEditorClient projectId={projectId} workflowId={workflowId} />
  );
}
