import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import DashboardLayout from "./components/DashboardLayout";
import Home from "./pages/Home";
import Settings from "./pages/Settings";
import WorkflowControl from "./pages/WorkflowControl";
import ScanHistory from "./pages/ScanHistory";
import PriceComparison from "./pages/PriceComparison";

function DashboardRouter() {
  return (
    <DashboardLayout>
      <Switch>
        <Route path={"/dashboard"} component={Home} />
        <Route path={"/dashboard/settings"} component={Settings} />
        <Route path={"/dashboard/workflows"} component={WorkflowControl} />
        <Route path={"/dashboard/history"} component={ScanHistory} />
        <Route path={"/dashboard/prices"} component={PriceComparison} />
        <Route component={NotFound} />
      </Switch>
    </DashboardLayout>
  );
}

function Router() {
  return (
    <Switch>
      <Route path={"/"} component={Home} />
      <Route path={"/dashboard/*"} component={DashboardRouter} />
      <Route path={"/404"} component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="light">
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
