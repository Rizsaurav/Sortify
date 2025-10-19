import { Button } from "./UI/ui-core"
import { Avatar, AvatarFallback, AvatarImage } from "./UI/ui-core"
import { Link } from "react-router-dom"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./UI/ui-core"
import { BellIcon, MoonIcon, SunIcon } from "@heroicons/react/24/outline"

export function Header() {
  return (
    <header className="h-16 border-b border-border bg-card">
      <div className="flex h-full items-center justify-between px-6">
        <div className="flex items-center gap-4">
          {/* Breadcrumb could go here */}
        </div>
        <div className="flex items-center gap-4">
          {/* Theme Toggle Button */}
          <Button variant="ghost" size="icon">
            <SunIcon className="h-5 w-5 rotate-0 scale-100 transition-all dark:rotate-90 dark:scale-0" />
            <MoonIcon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>
          {/* Notifications Button */}
          <Button variant="ghost" size="icon" className="relative">
            <BellIcon className="h-5 w-5" />
            <span className="absolute -top-1 -right-1 h-3 w-3 bg-primary rounded-full"></span>
            <span className="sr-only">Notifications</span>
          </Button>
          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                <Avatar className="h-10 w-10">
                  <AvatarImage src="/diverse-student-profiles.png" alt="Alex" />
                  <AvatarFallback>AS</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">Alex Smith</p>
                  <p className="text-xs leading-none text-muted-foreground">alex.smith@university.edu</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>Profile</DropdownMenuItem>
              <DropdownMenuItem>Settings</DropdownMenuItem>
              <DropdownMenuItem>Support</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>Log out</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          {/* Account Details SPA Link */}
          <Link
            to="/account-details"
            className="relative h-10 w-10 rounded-full p-0 flex items-center justify-center hover:ring-2 hover:ring-primary cursor-pointer"
            tabIndex={0}
            aria-label="Go to Account Details"
          >
            <Avatar className="h-10 w-10">
              <AvatarImage src="" alt="User avatar" />
              <AvatarFallback>AB</AvatarFallback>
            </Avatar>
          </Link>
        </div>
      </div>
    </header>
  )
}
