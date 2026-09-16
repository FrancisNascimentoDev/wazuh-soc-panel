const STATUS_LABELS = {
  operacional: "OPERACIONAL",
  atencao: "ATENÇÃO",
  indisponivel: "INDISPONÍVEL",
};

const STATUS_COLORS = {
  operacional: "green",
  atencao: "yellow",
  indisponivel: "red",
};

function setOverall(status) {
  const dot = document.getElementById("overall-dot");
  const text = document.getElementById("overall-text");
  dot.className = "dot " + (STATUS_COLORS[status] || "");
  const label =
    status === "operacional"
      ? "SISTEMA OPERACIONAL"
      : status === "atencao"
      ? "ATENÇÃO — VERIFICAR AGENTES"
      : "SISTEMA INDISPONÍVEL";
  text.textContent = label;
}

function renderServices(services) {
  const items = [
    { key: "docker", label: "Docker" },
    { key: "manager", label: "Wazuh Manager" },
    { key: "indexer", label: "Wazuh Indexer" },
    { key: "dashboard", label: "Wazuh Dashboard" },
  ];
  const list = document.getElementById("services-list");
  list.innerHTML = "";
  items.forEach((item) => {
    const svc = services[item.key] || { status: "indisponivel", ip: null };
    const color = svc.status === "operacional" ? "green" : "red";
    const ipLabel = svc.ip ? `<span class="ip">${svc.ip}</span>` : "";
    const li = document.createElement("li");
    li.className = "status-row";
    li.innerHTML = `
      <span class="dot ${color}"></span>
      <span class="name">${item.label}${ipLabel}</span>
      <span class="value">${(svc.status === "operacional" ? "OPERACIONAL" : "INDISPONÍVEL")}</span>
    `;
    list.appendChild(li);
  });
}

function renderAgents(agents, activeCount, totalCount) {
  const list = document.getElementById("agents-list");
  list.innerHTML = "";
  agents.forEach((agent) => {
    const color = agent.active ? "green" : "red";
    const statusLabel = agent.active ? "ACTIVE" : agent.status.toUpperCase();
    const ipLabel = agent.ip ? `<span class="ip">${agent.ip}</span>` : "";
    const li = document.createElement("li");
    li.className = "status-row";
    li.innerHTML = `
      <span class="dot ${color}"></span>
      <span class="name">${agent.id}  ${agent.name}${ipLabel}</span>
      <span class="value">${statusLabel}</span>
    `;
    list.appendChild(li);
  });
  document.getElementById("agents-summary").textContent =
    `${activeCount} / ${totalCount} AGENTES ATIVOS`;
}

async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();

    setOverall(data.overall_status);
    renderServices(data.docker_services);
    renderAgents(data.agents, data.agents_active, data.agents_total);

    document.getElementById("server-ip").textContent = data.server_ip;
    document.getElementById("wazuh-version").textContent = data.wazuh_version;
    document.getElementById("refresh-seconds").textContent = data.refresh_seconds;
  } catch (err) {
    setOverall("indisponivel");
    console.error("Falha ao consultar /api/status:", err);
  }
}

refreshStatus();
setInterval(refreshStatus, 10000);
