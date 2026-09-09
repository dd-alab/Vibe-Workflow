import ProjectDetailView from "../../../components/projects/ProjectDetailView";

export default async function ProjectPage({ params }) {
  const { projectId } = await params;
  return <ProjectDetailView projectId={projectId} />;
}
