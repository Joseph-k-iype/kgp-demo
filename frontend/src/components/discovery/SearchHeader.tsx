"use client";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import SearchBox from "./SearchBox";
import { prepareSearch } from "@/api/discovery";
import { useSession } from "@/components/Shell";
export default function SearchHeader({
  query,
  domainId,
}: {
  query: string;
  domainId: string | null;
}) {
  const router = useRouter();
  const { persona } = useSession();
  return (
    <div className="discovery-search-header">
      <Link href="/" className="back-to-search">
        <ArrowLeft size={15} />
        Back to search
      </Link>
      <SearchBox
        compact
        query={query}
        domainId={domainId}
        onSubmit={(value) =>
          router.push(prepareSearch(value, persona), { scroll: false })
        }
      />
    </div>
  );
}
