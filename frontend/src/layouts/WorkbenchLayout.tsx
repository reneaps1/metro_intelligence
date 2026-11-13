import { Outlet } from "react-router-dom";
import { EditionProvider } from "../lib/edition/EditionProvider";

// Full-viewport layout for desktop-style workbench modules (industrial demo).
// No platform sidebar/topbar: the workbench brings its own chrome.
export function WorkbenchLayout() {
  return (
    <EditionProvider>
      <div className="h-full">
        <Outlet />
      </div>
    </EditionProvider>
  );
}
