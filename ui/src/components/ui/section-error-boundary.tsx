import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  /** Compact fallback text shown when the section crashes. */
  fallback?: string;
}

interface State {
  hasError: boolean;
}

/**
 * Lightweight error boundary for panel sections.
 *
 * Catches rendering errors in children and shows a minimal fallback
 * instead of crashing the entire panel / page.
 */
export class SectionErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[SectionErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center rounded-lg border border-border/40 bg-muted/20 px-3 py-2 text-[10px] text-muted-foreground/50">
          {this.props.fallback ?? "Something went wrong"}
        </div>
      );
    }
    return this.props.children;
  }
}
