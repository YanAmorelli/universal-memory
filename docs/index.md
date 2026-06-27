---
hide:
  - navigation
  - toc
---

<section class="umem-hero">
  <div class="umem-hero__inner">
    <div>
      <p class="umem-kicker">Universal Memory for AI agents</p>
      <h1>Portable context for every coding agent.</h1>
      <p class="umem-lede">
        Universal Memory stores durable preferences, project facts, operating
        rules, and reusable skills so agents can continue work across sessions,
        hosts, and models without the same setup conversation every time.
      </p>
      <div class="umem-actions">
        <a class="umem-button umem-button--primary" href="users/getting-started/">Get started</a>
        <a class="umem-button" href="agents/operating-protocol/">Agent protocol</a>
        <a class="umem-button" href="contributors/architecture/">Architecture</a>
      </div>
    </div>
    <div class="umem-terminal" aria-label="Universal Memory CLI example">
      <div class="umem-terminal__bar"><span></span><span></span><span></span></div>
      <pre><code>$ umem init --runtime codex --runtime claude_code
$ umem remember "Prefer typed Python and clean architecture." --scope project
$ umem context --scope project --format json

{
  "ok": true,
  "operation": "context",
  "scope": "project",
  "data": { "summary": "..." }
}</code></pre>
    </div>
  </div>
</section>

<section class="umem-section">
  <h2>Choose your path</h2>
  <div class="umem-grid">
    <a class="umem-card" href="users/getting-started/">
      <h3>Users</h3>
      <p>Install UMEM, initialize a project, and let your agent retrieve context and persist durable learnings safely.</p>
    </a>
    <a class="umem-card" href="contributors/development/">
      <h3>Contributors</h3>
      <p>Understand the clean architecture, validation commands, release readiness, and alpha validation flow.</p>
    </a>
    <a class="umem-card" href="agents/operating-protocol/">
      <h3>Agents and LLMs</h3>
      <p>Follow the operating protocol for context retrieval, durable memory, skills, and safe mutation.</p>
    </a>
  </div>
</section>

<section class="umem-band">
  <div class="umem-section">
    <h2>Designed for controlled persistence</h2>
    <div class="umem-grid">
      <a class="umem-card" href="reference/cli-mcp-parity/">
        <h3>CLI and MCP parity</h3>
        <p>The CLI is canonical. MCP exposes equivalent capabilities for agents and hosts.</p>
      </a>
      <a class="umem-card" href="users/safety-and-recovery/">
        <h3>Snapshots and audit</h3>
        <p>Automatic mutations go through validation, secret scanning, snapshots, and audit events.</p>
      </a>
      <a class="umem-card" href="reference/skill-lifecycle/">
        <h3>Reusable skills</h3>
        <p>Draft, validate, publish, and maintain canonical skills under <code>.umem/skills/</code>, then sync them into supported runtimes explicitly.</p>
      </a>
    </div>
    <div class="umem-pillrow" aria-label="Product properties">
      <span class="umem-pill">Local-first</span>
      <span class="umem-pill">Python 3.12+</span>
      <span class="umem-pill">Human-readable storage</span>
      <span class="umem-pill">Agent-safe mutation</span>
      <span class="umem-pill">Curated docs</span>
    </div>
  </div>
</section>

<section class="umem-section">
  <h2>How this site relates to the README</h2>
  <p>
    <code>README.md</code> remains the package and repository entrypoint. This
    MkDocs site is the curated documentation surface: task-oriented for users,
    architectural for contributors, and operational for agents.
  </p>
</section>
