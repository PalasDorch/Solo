/**
 * Bridge API Helper
 * Automatically adds Authorization header to all Bridge requests
 */

const BRIDGE_URL = import.meta.env.VITE_BRIDGE_URL || 'http://127.0.0.1:8500'
const BRIDGE_TOKEN = import.meta.env.VITE_BRIDGE_TOKEN || 'pala'

const headers = {
  'Authorization': `Bearer ${BRIDGE_TOKEN}`,
  'Content-Type': 'application/json',
}

export async function bridgeHealth() {
  const res = await fetch(`${BRIDGE_URL}/health`)
  return res.json()
}

export async function fsRead(path: string) {
  const res = await fetch(`${BRIDGE_URL}/fs/read`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ path }),
  })
  return res.json()
}

export async function fsSearch(query: string, include: string[] = ['**/*.py']) {
  const res = await fetch(`${BRIDGE_URL}/fs/search`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ query, include }),
  })
  return res.json()
}

export async function applyPatch(diff: string, dry_run: boolean = true) {
  const res = await fetch(`${BRIDGE_URL}/ops/apply_patch`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ diff, dry_run }),
  })
  return res.json()
}

export async function commitPush(message: string, branch: string = 'mirror') {
  const res = await fetch(`${BRIDGE_URL}/git/commit_push`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, branch }),
  })
  return res.json()
}

export async function stateGet() {
  const res = await fetch(`${BRIDGE_URL}/state/get`, {
    headers,
  })
  return res.json()
}

