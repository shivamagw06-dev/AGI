import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function SearchButton() {
  return (
    <Button
      variant="ghost"
      size="icon"
      className="rounded-full hover:bg-slate-100"
      aria-label="Search"
    >
      <Search className="h-5 w-5 text-slate-700" />
    </Button>
  );
}