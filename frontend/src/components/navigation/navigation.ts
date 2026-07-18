import { BarChart3, Disc3, Gauge, Home, Library, Settings, Sparkles } from "lucide-react";
import type { ElementType } from "react";

export type Page = "overview" | "top10" | "scores" | "patterns" | "report" | "recommendations" | "settings";

export interface NavigationItem {
  id: Page;
  label: string;
  icon: ElementType;
}

export const NAVIGATION_ITEMS: NavigationItem[] = [
  { id: "overview", label: "Overview", icon: Home },
  { id: "top10", label: "Top 10", icon: Disc3 },
  { id: "scores", label: "Scores", icon: Gauge },
  { id: "patterns", label: "Patterns", icon: BarChart3 },
  { id: "report", label: "Persona Report", icon: Sparkles },
  { id: "recommendations", label: "Recommendations", icon: Library },
  { id: "settings", label: "Settings", icon: Settings },
];

export const USE_REACT_BITS_DESKTOP_SIDEBAR = true;
