import { Component, type ReactNode, type ErrorInfo } from "react";

type Props = { children: ReactNode; fallback?: ReactNode };
type State = { hasError: boolean };

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  handleRetry = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center text-sm text-red-600 mb-4">
          <p className="font-medium mb-1">Error en el dashboard</p>
          <p className="text-xs text-red-400 mb-2">Ocurrió un error al cargar los indicadores</p>
          <button
            className="px-3 py-1 bg-red-500 text-white rounded-lg text-xs font-medium hover:bg-red-600"
            onClick={this.handleRetry}
          >
            Reintentar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
