#!/usr/bin/env python3
"""
Wazuh SOC Status Panel - Backend
Consulta Docker, systemd e o Wazuh Manager para reportar o estado
do laboratório em /api/status.

Requisitos: Python 3.8+, Flask, e o usuário que roda este processo
precisa ter permissão para executar `docker` e `systemctl status`
(normalmente: grupo `docker` + regra sudo NOPASSWD para o status do serviço).
"""

import subprocess
import re
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configuração — ajuste aqui se os nomes dos containers ou o serviço mudarem
# ---------------------------------------------------------------------------
CONFIG = {
    "server_ip": "192.168.91.128",
    "wazuh_version": "4.14.7",
    "refresh_seconds": 10,
    "containers": {
        "manager": "single-node-wazuh.manager-1",
        "indexer": "single-node-wazuh.indexer-1",
        "dashboard": "single-node-wazuh.dashboard-1",
    },
    "agents": [
        {"id": "001", "name": "ubuntu-lab"},
        {"id": "002", "name": "debian-lab"},
        {"id": "003", "name": "kali-lab"},
    ],
    "systemd_service": "wazuh-lab-startup.service",
}


def run(cmd, timeout=8):
    """Executa um comando e retorna (ok, stdout). Nunca lança exceção."""
    try:
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def docker_running(container_name):
    """True se o container existe e está com status 'running'."""
    ok, out = run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container_name]
    )
    return ok and out.strip() == "true"


def get_container_ip(container_name):
    """
    Retorna o(s) IP(s) do container em todas as redes Docker às quais
    ele está conectado (ex.: "172.19.0.2" ou "172.19.0.2, 172.20.0.3").
    Retorna None se o container não existir ou não tiver IP (parado).
    """
    ok, out = run(
        [
            "docker",
            "inspect",
            "-f",
            "{{range $net,$conf := .NetworkSettings.Networks}}{{$conf.IPAddress}} {{end}}",
            container_name,
        ]
    )
    if not ok:
        return None
    ips = [ip for ip in out.strip().split() if ip]
    return ", ".join(ips) if ips else None


def get_docker_services_status():
    services = {}
    for key, container in CONFIG["containers"].items():
        services[key] = {
            "status": "operacional" if docker_running(container) else "indisponivel",
            "ip": get_container_ip(container),
        }
    # Docker em si: se conseguimos rodar "docker info", está ok
    ok, _ = run(["docker", "info"])
    services["docker"] = {"status": "operacional" if ok else "indisponivel", "ip": None}
    return services


def get_agents_status():
    """
    Usa `agent_control -l` dentro do container do Manager para pegar o
    estado real reportado pelo Wazuh (Active / Disconnected / Never connected).
    """
    manager = CONFIG["containers"]["manager"]
    ok, out = run(
        ["docker", "exec", manager, "/var/ossec/bin/agent_control", "-l"]
    )

    agents_by_id = {}
    if ok:
        # Linhas no formato: "   ID: 001, Name: ubuntu-lab, IP: any, Active"
        for line in out.splitlines():
            m = re.search(
                r"ID:\s*(\d+),\s*Name:\s*([^,]+),.*?\b(Active|Disconnected|Never connected)\b",
                line,
            )
            if m:
                agent_id, name, status = m.groups()
                agents_by_id[agent_id.strip()] = status.strip()

    result = []
    for agent in CONFIG["agents"]:
        status = agents_by_id.get(agent["id"], "desconhecido")
        result.append(
            {
                "id": agent["id"],
                "name": agent["name"],
                "status": status,
                "active": status.lower() == "active",
                "ip": get_container_ip(agent["name"]),
            }
        )
    return result


def get_systemd_status():
    ok, out = run(["systemctl", "is-active", CONFIG["systemd_service"]])
    return out.strip() if out else ("active" if ok else "inactive")


@app.route("/api/status")
def api_status():
    docker_services = get_docker_services_status()
    agents = get_agents_status()
    systemd_status = get_systemd_status()

    active_count = sum(1 for a in agents if a["active"])
    total_count = len(agents)

    core_ok = all(
        docker_services.get(k, {}).get("status") == "operacional"
        for k in ("docker", "manager", "indexer", "dashboard")
    )

    if core_ok and active_count == total_count:
        overall = "operacional"
    elif core_ok and active_count > 0:
        overall = "atencao"
    else:
        overall = "indisponivel"

    return jsonify(
        {
            "overall_status": overall,
            "server_ip": CONFIG["server_ip"],
            "wazuh_version": CONFIG["wazuh_version"],
            "refresh_seconds": CONFIG["refresh_seconds"],
            "docker_services": docker_services,
            "agents": agents,
            "agents_active": active_count,
            "agents_total": total_count,
            "systemd_service": {
                "name": CONFIG["systemd_service"],
                "status": systemd_status,
            },
        }
    )


@app.route("/")
def index():
    return render_template("index.html", config=CONFIG)


if __name__ == "__main__":
    # host 0.0.0.0 para acessar de outra máquina na rede local
    app.run(host="0.0.0.0", port=5000, debug=False)
