import ContactSheet from "../../../../components/gallery/ContactSheet";

export default async function GalleryPage({ params }) {
  const { projectId } = await params;
  return <ContactSheet projectId={projectId} />;
}
