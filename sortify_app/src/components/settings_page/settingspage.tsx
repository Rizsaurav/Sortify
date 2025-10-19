// src/pages/Settings.tsx
import React from "react";
import { DashboardLayout } from "../landing_page/dashboard_layout";
import { Button, DropdownMenuCheckboxItem } from "../landing_page/UI/ui-core"; // Adjust import path as needed

export default function Settings() {
  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto p-8">
        <h2 className="text-2xl font-bold mb-6">Settings</h2>
        <section className="bg-card border rounded-lg p-6 shadow-md space-y-8">
          <div>
            <label className="flex items-center justify-between">
              <span>Enable Dark Mode</span>
              <DropdownMenuCheckboxItem /> {/* Use your styled Switch component */}
            </label>
          </div>
          <div>
            <label className="flex items-center justify-between">
              <span>Email Notifications</span>
              <DropdownMenuCheckboxItem />
            </label>
          </div>
          <div>
            <Button variant="destructive">Delete Account</Button>
          </div>
        </section>
      </div>
    </DashboardLayout>
  );
}
