import { BarChart3, Disc3, Home, Library, Settings, Sparkles } from "lucide-react";
import type { ElementType } from "react";

export type Page = "overview" | "top10" | "insights" | "report" | "recommendations" | "settings";

export interface NavigationItem {
  id: Page;
  label: string;
  icon: ElementType;
}

export const NAVIGATION_ITEMS: NavigationItem[] = [
  { id: "overview", label: "Overview", icon: Home },
  { id: "top10", label: "Top 10", icon: Disc3 },
  { id: "insights", label: "Insights", icon: BarChart3 },
  { id: "report", label: "Persona Report", icon: Sparkles },
  { id: "recommendations", label: "Recommendations", icon: Library },
  { id: "settings", label: "Settings", icon: Settings },
];
