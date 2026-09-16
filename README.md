# Wazuh SOC Status Panel

Painel web em tempo real para monitoramento de um laboratório SOC baseado em [Wazuh](https://wazuh.com/) rodando em Docker. Mostra o status do Manager, Indexer e Dashboard, o estado de conexão de cada agente e o IP de cada container, com atualização automática a cada 10 segundos.

```
┌──────────────────────────────────────────────┐
│              WAZUH STATUS                    │
│       PAINEL OPERACIONAL DO SOC              │
├──────────────────────────────────────────────┤
│       🟢 SISTEMA OPERACIONAL                 │
├──────────────────────────────────────────────┤
│ SERVIÇOS PRINCIPAIS                          │
│ 🟢 Docker                     OPERACIONAL    │
│ 🟢 Wazuh Manager  172.19.0.2  OPERACIONAL     │
│ 🟢 Wazuh Indexer  172.19.0.3  OPERACIONAL     │
│ 🟢 Wazuh Dashboard            OPERACIONAL     │
├──────────────────────────────────────────────┤
│ AGENTES                                       │
│ 🟢 001 ubuntu-lab  172.19.0.4   ACTIVE         │
│ 🟢 002 debian-lab  172.19.0.5   ACTIVE         │
│ 🟢 003 kali-lab    172.19.0.6   ACTIVE         │
│             3 / 3 AGENTES ATIVOS              │
├──────────────────────────────────────────────┤
│ Servidor: 192.168.91.128                      │
│ Wazuh: 4.14.7                                 │
│ Atualização automática: 10 segundos           │
└──────────────────────────────────────────────┘
```

## Funcionalidades

- Status em tempo real do Wazuh Manager, Indexer e Dashboard
- Status de conexão de cada agente (Active / Disconnected / Never connected), lido diretamente do `agent_control -l` do Wazuh
- IP de cada container, incluindo containers conectados a múltiplas redes Docker
- Status do serviço systemd responsável pela inicialização automática do laboratório
- Indicador geral do ambiente (🟢 Operacional / 🟡 Atenção / 🔴 Indisponível), calculado automaticamente
- Atualização automática do frontend a cada 10 segundos, sem recarregar a página

## Arquitetura

```
wazuh-panel/
├── app.py                # Backend Flask — rotas / e /api/status
├── requirements.txt      # Dependências Python
├── templates/
│   └── index.html        # Página principal
└── static/
    ├── style.css          # Estilo do painel
    └── panel.js           # Polling em /api/status e renderização
```

O backend consulta o host diretamente via `subprocess`:

| Fonte | Comando | Uso |
|---|---|---|
| Docker | `docker inspect -f {{.State.Running}}` | Status de cada container da stack |
| Docker | `docker inspect -f {{range ...}}{{.IPAddress}}{{end}}` | IP de cada container em todas as redes conectadas |
| Wazuh | `docker exec <manager> agent_control -l` | Estado real de conexão de cada agente |
| systemd | `systemctl is-active <service>` | Status do serviço de boot do laboratório |

## Requisitos

- Python 3.8+
- Docker instalado e em execução no mesmo host
- Usuário com permissão para rodar `docker` (pertencente ao grupo `docker`) e para consultar `systemctl`
- Stack Wazuh já implantada via Docker Compose (ver seção de configuração)

## Instalação

```bash
git clone https://github.com/SEU-USUARIO/wazuh-soc-panel.git
cd wazuh-soc-panel

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuração

Os nomes de containers, agentes e demais parâmetros ficam centralizados no dicionário `CONFIG`, no início de `app.py`:

```python
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
```

Ajuste esses valores conforme os nomes reais dos seus containers e agentes.

## Uso

```bash
source venv/bin/activate
python3 app.py
```

Acesse `http://<IP_DO_SERVIDOR>:5000`.

## Executando como serviço (systemd)

Para o painel subir automaticamente com o sistema operacional, crie `/etc/systemd/system/wazuh-panel.service`:

```ini
[Unit]
Description=Wazuh SOC Status Panel
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/caminho/para/wazuh-soc-panel
ExecStart=/caminho/para/wazuh-soc-panel/venv/bin/python3 app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable wazuh-panel.service
sudo systemctl start wazuh-panel.service
sudo systemctl status wazuh-panel.service
```

> O usuário definido em `User=` precisa pertencer ao grupo `docker`:
> `sudo usermod -aG docker ubuntu` (é necessário reiniciar a sessão ou a VM para o grupo valer).

## Endpoint da API

`GET /api/status` retorna um JSON com o estado completo do ambiente:

```json
{
  "overall_status": "operacional",
  "server_ip": "192.168.91.128",
  "wazuh_version": "4.14.7",
  "refresh_seconds": 10,
  "docker_services": {
    "docker": { "status": "operacional", "ip": null },
    "manager": { "status": "operacional", "ip": "172.19.0.2" },
    "indexer": { "status": "operacional", "ip": "172.19.0.3" },
    "dashboard": { "status": "operacional", "ip": "172.19.0.4" }
  },
  "agents": [
    { "id": "001", "name": "ubuntu-lab", "status": "Active", "active": true, "ip": "172.19.0.5" }
  ],
  "agents_active": 3,
  "agents_total": 3,
  "systemd_service": { "name": "wazuh-lab-startup.service", "status": "active" }
}
```

## Contexto do projeto

Este painel foi desenvolvido como parte de um laboratório de estudos de SOC com Wazuh 4.14.7 em Docker sobre Ubuntu Server 24.04, com múltiplos agentes Linux (Ubuntu, Debian, Kali) e automação completa de inicialização via systemd.

## Autor

**Francis Nascimento** 

## Licença

MIT

<img src="img/serv. rodando.jpeg" alt="serv. rodando">

![Logo da Minha Empresa](https://exemplo.com/logo.png)