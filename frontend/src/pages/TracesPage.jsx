import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { listTraces } from "../lib/api.js";

export default function TracesPage() {
  const { projectId } = useParams();
  const [traces, setTraces] = useState([]);

  useEffect(() => {
    listTraces(projectId).then(setTraces);
  }, [projectId]);

  return (
    <div className="mx-auto mt-12 max-w-3xl p-6">
      <h1 className="text-xl font-semibold">Traces</h1>
      <table className="mt-4 w-full text-left text-sm">
        <thead>
          <tr className="border-b">
            <th className="py-2">Name</th>
            <th>Status</th>
            <th>Spans</th>
            <th>Tokens</th>
            <th>Started</th>
          </tr>
        </thead>
        <tbody>
          {traces.map((t) => (
            <tr key={t.id} className="border-b">
              <td className="py-2">
                <Link to={`/traces/${t.id}`} className="underline">
                  {t.name}
                </Link>
              </td>
              <td>{t.status}</td>
              <td>{t.span_count}</td>
              <td>{t.total_tokens}</td>
              <td>{new Date(t.started_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
