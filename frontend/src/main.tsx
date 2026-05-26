import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles.css";

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state: Readonly<{ error: Error | null }> = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <main className="flex min-h-screen items-center justify-center bg-ink px-4 text-slate-100">
          <section className="max-w-xl border border-danger bg-danger/10 p-6">
            <p className="text-xs uppercase tracking-wider text-danger">Frontend error</p>
            <h1 className="mt-2 text-2xl font-semibold">FactoryOps could not render</h1>
            <p className="mt-3 text-sm text-slate-200">
              Refresh the page. If this keeps happening, check the browser console and frontend
              container logs.
            </p>
            <pre className="mt-4 overflow-auto border border-white/10 bg-black/20 p-3 text-xs text-slate-300">
              {this.state.error.message}
            </pre>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
