// src/components/ui-kit.tsx
"use client"

import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import * as AccordionPrimitive from "@radix-ui/react-accordion"
import * as AlertDialogPrimitive from "@radix-ui/react-alert-dialog"
import * as AspectRatioPrimitive from "@radix-ui/react-aspect-ratio"
import * as AvatarPrimitive from "@radix-ui/react-avatar"
import { ChevronDownIcon, ChevronRight, MoreHorizontal } from "lucide-react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "../../lib/utils"

// ------------------ Accordion ------------------
export function Accordion(props: React.ComponentProps<typeof AccordionPrimitive.Root>) {
  return <AccordionPrimitive.Root data-slot="accordion" {...props} />
}
export function AccordionItem({ className, ...props }: React.ComponentProps<typeof AccordionPrimitive.Item>) {
  return <AccordionPrimitive.Item data-slot="accordion-item" className={cn("border-b last:border-b-0", className)} {...props} />
}
export function AccordionTrigger({ className, children, ...props }: React.ComponentProps<typeof AccordionPrimitive.Trigger>) {
  return (
    <AccordionPrimitive.Header className="flex">
      <AccordionPrimitive.Trigger
        data-slot="accordion-trigger"
        className={cn(
          "flex flex-1 items-start justify-between py-4 text-left text-sm font-medium transition-all hover:underline",
          "focus-visible:ring-ring/50 focus-visible:ring-[3px] rounded-md outline-none disabled:pointer-events-none disabled:opacity-50 [&[data-state=open]>svg]:rotate-180",
          "min-h-[44px]",
          className
        )}
        {...props}
      >
        {children}
        <ChevronDownIcon className="text-muted-foreground size-4 shrink-0 transition-transform ml-2" />
      </AccordionPrimitive.Trigger>
    </AccordionPrimitive.Header>
  )
}
export function AccordionContent({ className, children, ...props }: React.ComponentProps<typeof AccordionPrimitive.Content>) {
  return (
    <AccordionPrimitive.Content data-slot="accordion-content" className="overflow-hidden text-sm data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down" {...props}>
      <div className={cn("pb-4 pt-1", className)}>{children}</div>
    </AccordionPrimitive.Content>
  )
}

// ------------------ AlertDialog ------------------
export function AlertDialog(props: React.ComponentProps<typeof AlertDialogPrimitive.Root>) {
  return <AlertDialogPrimitive.Root data-slot="alert-dialog" {...props} />
}
export const AlertDialogTrigger = AlertDialogPrimitive.Trigger
export const AlertDialogPortal = AlertDialogPrimitive.Portal
export function AlertDialogOverlay({ className, ...props }: React.ComponentProps<typeof AlertDialogPrimitive.Overlay>) {
  return (
    <AlertDialogPrimitive.Overlay
      data-slot="alert-dialog-overlay"
      className={cn("fixed inset-0 z-50 bg-black/50 data-[state=open]:animate-in data-[state=closed]:animate-out", className)}
      {...props}
    />
  )
}
export function AlertDialogContent({ className, ...props }: React.ComponentProps<typeof AlertDialogPrimitive.Content>) {
  return (
    <AlertDialogPortal>
      <AlertDialogOverlay />
      <AlertDialogPrimitive.Content
        data-slot="alert-dialog-content"
        className={cn("fixed top-1/2 left-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border bg-background p-6 shadow-lg mx-4 sm:mx-0", className)}
        {...props}
      />
    </AlertDialogPortal>
  )
}
export const AlertDialogHeader = (p: React.ComponentProps<"div">) => <div data-slot="alert-dialog-header" className={cn("flex flex-col gap-2 text-center sm:text-left", p.className)} {...p} />
export const AlertDialogFooter = (p: React.ComponentProps<"div">) => <div data-slot="alert-dialog-footer" className={cn("flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-2", p.className)} {...p} />
export const AlertDialogTitle = (p: React.ComponentProps<typeof AlertDialogPrimitive.Title>) => <AlertDialogPrimitive.Title data-slot="alert-dialog-title" className={cn("text-lg font-semibold", p.className)} {...p} />
export const AlertDialogDescription = (p: React.ComponentProps<typeof AlertDialogPrimitive.Description>) => <AlertDialogPrimitive.Description data-slot="alert-dialog-description" className={cn("text-sm text-muted-foreground", p.className)} {...p} />
export const AlertDialogAction = AlertDialogPrimitive.Action
export const AlertDialogCancel = AlertDialogPrimitive.Cancel

// ------------------ Alert ------------------
const alertVariants = cva("relative w-full rounded-lg border px-4 py-3 text-sm grid items-start", {
  variants: {
    variant: {
      default: "bg-card text-card-foreground",
      destructive: "text-destructive bg-card",
    },
    defaultVariants: { variant: "default" },
  },
})
export function Alert({ className, variant, ...props }: React.ComponentProps<"div"> & VariantProps<typeof alertVariants>) {
  return <div data-slot="alert" role="alert" className={cn(alertVariants({ variant }), className)} {...props} />
}
export const AlertTitle = (p: React.ComponentProps<"div">) => <div data-slot="alert-title" className={cn("font-medium mb-1", p.className)} {...p} />
export const AlertDescription = (p: React.ComponentProps<"div">) => <div data-slot="alert-description" className={cn("text-sm text-muted-foreground [&_p]:leading-relaxed", p.className)} {...p} />

// ------------------ AspectRatio ------------------
export function AspectRatio(props: React.ComponentProps<typeof AspectRatioPrimitive.Root>) {
  return <AspectRatioPrimitive.Root data-slot="aspect-ratio" {...props} />
}

// ------------------ Avatar ------------------
export function Avatar({ className, ...props }: React.ComponentProps<typeof AvatarPrimitive.Root>) {
  return <AvatarPrimitive.Root data-slot="avatar" className={cn("relative flex size-9 overflow-hidden rounded-full sm:size-8", className)} {...props} />
}
export function AvatarImage({ className, ...props }: React.ComponentProps<typeof AvatarPrimitive.Image>) {
  return <AvatarPrimitive.Image data-slot="avatar-image" className={cn("aspect-square size-full", className)} {...props} />
}
export function AvatarFallback({ className, ...props }: React.ComponentProps<typeof AvatarPrimitive.Fallback>) {
  return <AvatarPrimitive.Fallback data-slot="avatar-fallback" className={cn("flex size-full items-center justify-center rounded-full bg-muted", className)} {...props} />
}

// ------------------ Badge ------------------
const badgeVariants = cva("inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium sm:px-2 sm:py-0.5", {
  variants: {
    variant: {
      default: "bg-primary text-primary-foreground",
      secondary: "bg-secondary text-secondary-foreground",
      destructive: "bg-destructive text-white",
      outline: "border text-foreground",
    },
    defaultVariants: { variant: "default" },
  },
})
export function Badge({ className, variant, asChild = false, ...props }: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "span"
  return <Comp data-slot="badge" className={cn(badgeVariants({ variant }), className)} {...props} />
}

// ------------------ Breadcrumb ------------------
export const Breadcrumb = (p: React.ComponentProps<"nav">) => <nav aria-label="breadcrumb" data-slot="breadcrumb" {...p} />
export const BreadcrumbList = (p: React.ComponentProps<"ol">) => <ol data-slot="breadcrumb-list" className={cn("flex flex-wrap items-center gap-1.5 text-sm text-muted-foreground sm:gap-1.5", p.className)} {...p} />
export const BreadcrumbItem = (p: React.ComponentProps<"li">) => <li data-slot="breadcrumb-item" className={cn("inline-flex items-center gap-1.5 min-h-[24px]", p.className)} {...p} />
export function BreadcrumbLink({ asChild, className, ...props }: React.ComponentProps<"a"> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "a"
  return <Comp data-slot="breadcrumb-link" className={cn("hover:text-foreground transition-colors min-h-[44px] inline-flex items-center sm:min-h-0", className)} {...props} />
}
export const BreadcrumbPage = (p: React.ComponentProps<"span">) => <span data-slot="breadcrumb-page" aria-current="page" className={cn("font-normal text-foreground", p.className)} {...p} />
export const BreadcrumbSeparator = ({ children, className, ...props }: React.ComponentProps<"li">) => (
  <li data-slot="breadcrumb-separator" className={cn("[&>svg]:size-3.5", className)} {...props}>
    {children ?? <ChevronRight />}
  </li>
)
export const BreadcrumbEllipsis = (p: React.ComponentProps<"span">) => (
  <span data-slot="breadcrumb-ellipsis" className={cn("flex size-10 items-center justify-center sm:size-9", p.className)} {...p}>
    <MoreHorizontal className="size-4" />
    <span className="sr-only">More</span>
  </span>
)