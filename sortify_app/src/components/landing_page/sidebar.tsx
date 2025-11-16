import { cn } from "../lib/utils"
import { Badge, Button } from "./UI/ui-core"
import {
  AcademicCapIcon,
  BeakerIcon,
  BookOpenIcon,
  CalculatorIcon,
  ChartBarIcon,
  CloudArrowUpIcon,
  CogIcon,
  DocumentIcon,
  FolderIcon,
  HomeIcon,
  MagnifyingGlassIcon,
  PresentationChartLineIcon,
} from "@heroicons/react/24/outline"

// Constants
const SIDEBAR_WIDTH = "w-64"
const LOGO_HEIGHT = "h-16"
const ICON_SIZE = "w-5 h-5"
const BUTTON_HEIGHT = "h-10"

// Navigation configuration
const navigation = [
  { name: "Dashboard", href: "#", icon: HomeIcon, current: true },
  { name: "All Files", href: "#", icon: DocumentIcon, count: 1247 },
  { name: "Search", href: "#", icon: MagnifyingGlassIcon },
  { name: "Upload", href: "#", icon: CloudArrowUpIcon },
]

// Category configuration
const categories = [
  { name: "Assignments", icon: BookOpenIcon, count: 89, color: "bg-blue-500" },
  { name: "Lectures", icon: AcademicCapIcon, count: 156, color: "bg-green-500" },
  { name: "Research", icon: BeakerIcon, count: 34, color: "bg-purple-500" },
  { name: "Math", icon: CalculatorIcon, count: 67, color: "bg-orange-500" },
  { name: "Presentations", icon: PresentationChartLineIcon, count: 23, color: "bg-pink-500" },
]

// Quick actions configuration
const quickActions = [
  { name: "Analytics", href: "#", icon: ChartBarIcon },
  { name: "Settings", href: "#", icon: CogIcon },
]

// Helper function to get navigation button styles
const getNavigationButtonStyles = (isActive: boolean) => {
  return cn(
    "w-full justify-start gap-3",
    BUTTON_HEIGHT,
    isActive
      ? "bg-sidebar-accent text-sidebar-accent-foreground"
      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
  )
}

export function Sidebar() {
  return (
    <div className={cn("flex h-screen flex-col bg-sidebar border-r border-sidebar-border", SIDEBAR_WIDTH)}>
      {/* Logo */}
      <div className={cn("flex items-center px-6 border-b border-sidebar-border", LOGO_HEIGHT)}>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <FolderIcon className={cn(ICON_SIZE, "text-primary-foreground")} />
          </div>
          <span className="text-xl font-bold text-sidebar-foreground">Sortify</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-8">
        {/* Main Navigation */}
        <div>
          <h3 className="text-xs font-semibold text-sidebar-foreground/60 uppercase tracking-wider mb-3">Navigation</h3>
          <ul className="space-y-1">
            {navigation.map((item) => (
              <li key={item.name}>
                <Button
                  variant={item.current ? "secondary" : "ghost"}
                  className={getNavigationButtonStyles(item.current || false)}
                >
                  <item.icon className={ICON_SIZE} />
                  <span className="flex-1 text-left">{item.name}</span>
                  {item.count && (
                    <Badge variant="secondary" className="ml-auto">
                      {item.count}
                    </Badge>
                  )}
                </Button>
              </li>
            ))}
          </ul>
        </div>

        {/* Categories */}
        <div>
          <h3 className="text-xs font-semibold text-sidebar-foreground/60 uppercase tracking-wider mb-3">Categories</h3>
          <ul className="space-y-1">
            {categories.map((category) => (
              <li key={category.name}>
                <Button
                  variant="ghost"
                  className={cn(
                    "w-full justify-start gap-3 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    BUTTON_HEIGHT
                  )}
                >
                  <div className={cn("w-3 h-3 rounded-full", category.color)} />
                  <span className="flex-1 text-left">{category.name}</span>
                  <Badge variant="outline" className="ml-auto">
                    {category.count}
                  </Badge>
                </Button>
              </li>
            ))}
          </ul>
        </div>

        {/* Quick Actions */}
        <div className="mt-auto">
          <h3 className="text-xs font-semibold text-sidebar-foreground/60 uppercase tracking-wider mb-3">
            Quick Actions
          </h3>
          <ul className="space-y-1">
            {quickActions.map((item) => (
              <li key={item.name}>
                <Button
                  variant="ghost"
                  className={cn(
                    "w-full justify-start gap-3 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    BUTTON_HEIGHT
                  )}
                >
                  <item.icon className={ICON_SIZE} />
                  {item.name}
                </Button>
              </li>
            ))}
          </ul>
        </div>
      </nav>
    </div>
  )
}