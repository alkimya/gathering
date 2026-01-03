import { Component } from 'react';
import type { ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });
    this.props.onError?.(error, errorInfo);

    // Log to console in development
    if (import.meta.env.DEV) {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-[400px] flex items-center justify-center p-8">
          <div className="glass-card rounded-2xl p-8 max-w-lg w-full text-center">
            {/* Icon */}
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-500 to-orange-500 glow-red flex items-center justify-center mx-auto mb-6">
              <AlertTriangle className="w-8 h-8 text-white" />
            </div>

            {/* Title */}
            <h2 className="text-xl font-bold text-white mb-2">Something went wrong</h2>
            <p className="text-zinc-400 mb-6">
              An unexpected error occurred. Please try again or return to the dashboard.
            </p>

            {/* Error details (development only) */}
            {import.meta.env.DEV && this.state.error && (
              <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-left">
                <div className="flex items-center gap-2 text-red-400 text-sm font-medium mb-2">
                  <Bug className="w-4 h-4" />
                  Error Details
                </div>
                <p className="text-xs text-red-300 font-mono break-all">
                  {this.state.error.message}
                </p>
                {this.state.errorInfo?.componentStack && (
                  <details className="mt-2">
                    <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-400">
                      Component Stack
                    </summary>
                    <pre className="mt-2 text-xs text-zinc-500 overflow-x-auto max-h-32">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </details>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={this.handleRetry}
                className="flex-1 px-4 py-2.5 bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white rounded-xl font-medium transition-all flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
              <button
                onClick={this.handleGoHome}
                className="flex-1 btn-gradient px-4 py-2.5 rounded-xl font-medium flex items-center justify-center gap-2"
              >
                <Home className="w-4 h-4" />
                Go to Dashboard
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Hook for functional components to throw errors to the boundary
export function useErrorBoundary() {
  const throwError = (error: Error) => {
    throw error;
  };

  return { throwError };
}

export default ErrorBoundary;
