import { useCallback, useEffect, useState } from "react";

export type CircuitNode = {
  id: string;
  componentKey: string;
  type: "board" | "input" | "output" | "passive" | "power";
  label: string;
  position: {
    x: number;
    y: number;
  };
  data: Record<string, unknown>;
};

export type CircuitEdge = {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
  targetHandle?: string | null;
  label?: string | null;
  data: Record<string, unknown>;
};

export type CircuitResponse = {
  id: string;
  title: string;
  userPrompt: string;
  summary: string;
  nodes: CircuitNode[];
  edges: CircuitEdge[];
  code: string;
  warnings: string[];
  explanation: string[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export function useCircuitDemo() {
  const [circuit, setCircuit] = useState<CircuitResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDemo = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/circuit/demo`);

      if (!response.ok) {
        throw new Error(`API responded with ${response.status}`);
      }

      const data = (await response.json()) as CircuitResponse;
      setCircuit(data);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const generateCircuit = useCallback(async (prompt: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/circuit/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        throw new Error(`API responded with ${response.status}`);
      }

      const data = (await response.json()) as CircuitResponse;
      setCircuit(data);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDemo();
  }, [loadDemo]);

  return {
    circuit,
    error,
    generateCircuit,
    isLoading,
    loadDemo,
  };
}
