# 🛰️ Cisco ThousandEyes + CML + Splunk Cloud Integration

## 📌 Objectives

This project demonstrates how to:
- Run ThousandEyes agents on a simulated topology using Cisco Modeling Labs (CML).
- Forward ThousandEyes test results and alerts into **Splunk Cloud** for analysis.
- Optionally use **Splunk Universal Forwarder** to route data from a node when HTTP Event Collector (HEC) integration is not working.
- Troubleshoot and validate end-to-end data flow using CLI tools like `curl`, `openssl`, `keytool`, and `splunk`.

---

## 🖥️ Devices

| Name        | Role                     | Notes                            |
|-------------|--------------------------|----------------------------------|
| `ubuntu-te` | ThousandEyes Enterprise Agent | Dockerized agent, also used for Splunk UF |
| `router-1`  | Core router               | Part of the CML topology         |
| `server-1`  | Optional test target      | Used for ThousandEyes tests      |

---

## 🧱 Platforms

- **Cisco Modeling Labs (CML)**  
  Simulates the test environment (routers, endpoints, etc.)

- **Cisco ThousandEyes (TE)**  
  Cloud-based monitoring service. Configured with agents and tests.

- **Splunk Cloud**  
  Cloud-based log and metrics aggregation. Receives TE alerts.

---

## 🔌 Integration Steps

---

## 1. 🧪 ThousandEyes Agent (on `ubuntu-te`)

Install and run the agent via Docker:
```bash
docker run --rm -d --name te-agent \
  --net=host \
  --cap-add=NET_ADMIN \
  -e TEAGENT_ACCOUNT_TOKEN=<your_token> \
  thousandeyes/enterprise-agent
