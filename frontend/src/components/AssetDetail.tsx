"use client";
import ContentViewer from "./discovery/ContentViewer";
export default function AssetDetail({
  id,
  onClose,
}: {
  id: string;
  onClose: () => void;
}) {
  return <ContentViewer handle={{ kind: "asset", id }} onClose={onClose} />;
}
