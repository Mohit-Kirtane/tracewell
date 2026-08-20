import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { createApiKey, listApiKeys, revokeApiKey } from "../lib/api.js";

export default function ApiKeysPage() {
  const { projectId } = useParams();
  const [keys, setKeys] = useState([]);
  const [justCreated, setJustCreated] = useState(null);

  async function refresh() {
    setKeys(await listApiKeys(projectId));
  }

  useEffect(() => {
    refresh();
  }, [projectId]);

  async function handleCreate() {
    const created = await createApiKey(projectId);
    setJustCreated(created.key);
    await refresh();
  }

  async function handleRevoke(keyId) {
    await revokeApiKey(projectId, keyId);
    await refresh();
  }

  return (
    <div className="mx-auto mt-12 max-w-2xl p-6">
      <h1 className="text-xl font-semibold">API keys</h1>
      <button onClick={handleCreate} className="mt-4 rounded bg-black px-4 py-2 text-white">
        Generate new key
      </button>
      {justCreated && (
        <p className="mt-3 rounded border border-yellow-500 bg-yellow-50 p-3 font-mono text-sm">
          {justCreated} — copy this now, it won't be shown again.
        </p>
      )}
      <ul className="mt-6 flex flex-col gap-2">
        {keys.map((k) => (
          <li key={k.id} className="flex items-center justify-between rounded border p-3">
            <span className="font-mono text-sm">
              {k.prefix}… {k.revoked_at && "(revoked)"}
            </span>
            {!k.revoked_at && (
              <button onClick={() => handleRevoke(k.id)} className="text-sm text-red-600 underline">
                Revoke
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
