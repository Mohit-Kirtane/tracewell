import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Check, Copy, KeyRound } from "lucide-react";
import { createApiKey, listApiKeys, revokeApiKey } from "../lib/api.js";

export default function ApiKeysPage() {
  const { projectId } = useParams();
  const [keys, setKeys] = useState(null);
  const [justCreated, setJustCreated] = useState(null);
  const [copied, setCopied] = useState(false);
  const [creating, setCreating] = useState(false);

  async function refresh() {
    setKeys(await listApiKeys(projectId));
  }

  useEffect(() => {
    refresh();
  }, [projectId]);

  async function handleCreate() {
    setCreating(true);
    try {
      const created = await createApiKey(projectId);
      setJustCreated(created.key);
      setCopied(false);
      await refresh();
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(keyId) {
    await revokeApiKey(projectId, keyId);
    await refresh();
  }

  function handleCopy() {
    navigator.clipboard.writeText(justCreated);
    setCopied(true);
  }

  return (
    <div>
      <div className="flex items-center justify-between border-b border-border pb-5">
        <h1 className="font-display text-xl font-semibold text-text">API keys</h1>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="flex items-center gap-1.5 rounded-md bg-signal px-4 py-2 font-body text-sm font-medium text-white transition hover:bg-signal-deep disabled:opacity-50"
        >
          <KeyRound className="h-3.5 w-3.5" />
          Generate new key
        </button>
      </div>

      {justCreated && (
        <div className="mt-5 rounded-lg border border-warn bg-warn-tint px-4 py-3.5">
          <p className="font-body text-xs font-medium text-warn">
            Copy this now — it won't be shown again.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <code className="flex-1 truncate rounded-md border border-border bg-surface px-3 py-2 font-mono text-sm text-text">
              {justCreated}
            </code>
            <button
              onClick={handleCopy}
              className="flex shrink-0 items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-2 font-body text-sm text-text transition hover:border-signal"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-ok" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      )}

      {keys === null ? null : keys.length === 0 ? (
        <div className="mt-6 rounded-lg border border-dashed border-border-strong px-6 py-10 text-center">
          <p className="font-body text-sm text-text-dim">
            No API keys yet. Generate one to start sending traces from tracewell-sdk.
          </p>
        </div>
      ) : (
        <ul className="mt-6 flex flex-col gap-2">
          {keys.map((k) => (
            <li
              key={k.id}
              className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <code className="font-mono text-sm text-text">{k.prefix}…</code>
                {k.revoked_at && (
                  <span className="rounded-full bg-surface-sunken px-2 py-0.5 font-body text-xs text-text-faint">
                    Revoked
                  </span>
                )}
              </div>
              {!k.revoked_at && (
                <button
                  onClick={() => handleRevoke(k.id)}
                  className="font-body text-sm text-danger transition hover:text-red-700"
                >
                  Revoke
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
