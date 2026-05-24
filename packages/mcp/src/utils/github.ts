export interface PrOptions {
  owner: string;
  repo: string;
  title: string;
  body: string;
  branch: string;
  baseBranch?: string;
  files: Array<{ path: string; content: string }>;
}

export async function createPullRequest(
  token: string,
  options: PrOptions
): Promise<string> {
  const { owner, repo, title, body, branch, baseBranch = "main", files } = options;
  const baseUrl = `https://api.github.com/repos/${owner}/${repo}`;
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github.v3+json",
    "Content-Type": "application/json",
  };

  const refRes = await fetch(`${baseUrl}/git/ref/heads/${baseBranch}`, { headers });
  if (!refRes.ok) throw new Error(`Failed to get base ref: ${refRes.status}`);
  const refData = (await refRes.json()) as { object: { sha: string } };
  const baseSha = refData.object.sha;

  const createRefRes = await fetch(`${baseUrl}/git/refs`, {
    method: "POST",
    headers,
    body: JSON.stringify({ ref: `refs/heads/${branch}`, sha: baseSha }),
  });
  if (!createRefRes.ok && (await createRefRes.text()).includes("Reference already exists")) {
    // Branch already exists — update it
  } else if (!createRefRes.ok) {
    throw new Error(`Failed to create branch: ${createRefRes.status}`);
  }

  for (const file of files) {
    const encoded = Buffer.from(file.content).toString("base64");
    let existingSha: string | undefined;

    const getRes = await fetch(`${baseUrl}/contents/${file.path}?ref=${branch}`, { headers });
    if (getRes.ok) {
      const existing = (await getRes.json()) as { sha: string };
      existingSha = existing.sha;
    }

    const putRes = await fetch(`${baseUrl}/contents/${file.path}`, {
      method: "PUT",
      headers,
      body: JSON.stringify({
        message: `Update ${file.path}`,
        content: encoded,
        branch,
        ...(existingSha ? { sha: existingSha } : {}),
      }),
    });
    if (!putRes.ok) throw new Error(`Failed to create file ${file.path}: ${putRes.status}`);
  }

  const prRes = await fetch(`${baseUrl}/pulls`, {
    method: "POST",
    headers,
    body: JSON.stringify({ title, body, head: branch, base: baseBranch }),
  });
  if (!prRes.ok) {
    const errText = await prRes.text();
    if (errText.includes("A pull request already exists")) {
      const listRes = await fetch(`${baseUrl}/pulls?head=${owner}:${branch}&state=open`, {
        headers,
      });
      if (listRes.ok) {
        const pulls = (await listRes.json()) as Array<{ html_url: string }>;
        if (pulls.length > 0) return pulls[0].html_url;
      }
      return `PR already exists for branch ${branch}`;
    }
    throw new Error(`Failed to create PR: ${prRes.status} ${errText}`);
  }

  const prData = (await prRes.json()) as { html_url: string };
  return prData.html_url;
}
