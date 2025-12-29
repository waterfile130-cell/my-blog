---
title: "Building a Keepalived + Nginx Dual-Master HA Cluster from Scratch (Ubuntu 24.04)"
date: 2025-12-23
image:
categories: [Tech, DevOps, Linux, High Availability]
tags: [nginx, keepalived, ubuntu, load-balancing]
---

# Building a Keepalived + Nginx Dual-Master HA Cluster from Scratch (Ubuntu 24.04)

> **Preface**:
> I recently grabbed a domain for just a dollar and decided to tinker with server high availability architectures.
> In a production environment, a single point of failure (SPOF) is a DevOps nightmare. Today, I'm documenting how I used Keepalived to implement a **Dual-Master (Active-Active)** architecture.
>
> **Goal**: Two servers acting as backups for each other. Normally, each handles one VIP (Virtual IP). If one server fails, the other instantly takes over all traffic!

## 🛠️ Environment Preparation

| Role | Hostname | IP Address | Interface | Initial Task |
| :--- | :--- | :--- | :--- | :--- |
| **Node A** | ubuntu-13 | 10.0.0.13 | `ens33` | **Master (VIP1)** / Backup (VIP2) |
| **Node B** | ubuntu-16 | 10.0.0.16 | `eth0` | Backup (VIP1) / **Master (VIP2)** |
| **VIP 1** | - | **10.0.0.100** | - | Primary Entry Point |
| **VIP 2** | - | **10.0.0.200** | - | Secondary/Load Balancing Entry Point |

> **Note**: My two machines have different network interface names (`ens33` vs `eth0`). This caused some issues during configuration, so please verify your own interface names using `ip addr` before proceeding!

---

## 1. Installing Software

Execute the following commands on **both** machines:

```bash
sudo apt update
sudo apt install -y keepalived nginx net-tools
```

To easily verify the failover effect, let's modify the default Nginx index page to display different content on each node:

**On Node A (10.0.0.13):**
```bash
echo "<h1>I am Node A (13)</h1>" | sudo tee /var/www/html/index.nginx-debian.html
```

**On Node B (10.0.0.16):**
```bash
echo "<h1>I am Node B (16)</h1>" | sudo tee /var/www/html/index.nginx-debian.html
```

---

## 2. Configuring Health Check Script

Keepalived needs a script to determine if the service is down. We'll create a simple script that checks for the existence of a specific file to simulate a failure (this can later be changed to check for the Nginx process).

**Perform this on both machines:**

```bash
# Create the directory for scripts
sudo mkdir -p /etc/keepalived/scripts

# Create the script file
sudo nano /etc/keepalived/scripts/check_fail.sh
```

**Script Content:**

```bash
#!/bin/bash
# If the file /tmp/keepalived.fail exists, return 1 (failure), triggering a priority downgrade.
if [ -f "/tmp/keepalived.fail" ]; then
    exit 1
else
    exit 0
fi
```

**Grant execution permissions (Crucial!):**
```bash
sudo chmod +x /etc/keepalived/scripts/check_fail.sh
```

---

## 3. Core Configuration: Active-Active Setup

This is the most critical part. We use the VRRP protocol to let the two machines monitor each other.

### 📄 Node A (192.168.8.13) Configuration
Edit `/etc/keepalived/keepalived.conf`:

```nginx
global_defs {
    router_id NODE_A
    script_user root
    enable_script_security
}

# Define the health check script
vrrp_script chk_manual {
    script "/etc/keepalived/scripts/check_fail.sh"
    interval 2
    weight -30
}

# Instance 1: I am MASTER, claiming VIP 100
vrrp_instance VI_1 {
    state MASTER
    interface ens33         # ⚠️ Note: Use your actual interface name
    virtual_router_id 50    # ID must match on both sides
    priority 100            # Higher score = Master
    advert_int 1
    unicast_src_ip 10.0.0.13
    unicast_peer {
        10.0.0.16
    }
    authentication {
        auth_type PASS
        auth_pass 1111
    }
    virtual_ipaddress {
        10.0.0.100 dev ens33 label ens33:1
    }
    track_script {
        chk_manual
    }
}

# Instance 2: I am BACKUP, standby for VIP 200
vrrp_instance VI_2 {
    state BACKUP
    interface ens33
    virtual_router_id 60    # ID must be unique and match on both sides
    priority 90             # Lower score = Backup
    advert_int 1
    unicast_src_ip 192.168.8.13
    unicast_peer {
        192.168.8.16
    }
    authentication {
        auth_type PASS
        auth_pass 2222
    }
    virtual_ipaddress {
        10.0.0.200 dev ens33 label ens33:2
    }
    track_script {
        chk_manual
    }
}
```

---

### 📄 Node B (192.168.8.16) Configuration
Edit `/etc/keepalived/keepalived.conf`:

```nginx
global_defs {
    router_id NODE_B
    script_user root
    enable_script_security
}

vrrp_script chk_manual {
    script "/etc/keepalived/scripts/check_fail.sh"
    interval 2
    weight -30
}

# Instance 1: I am BACKUP, standby for VIP 100
vrrp_instance VI_1 {
    state BACKUP
    interface eth0          # ⚠️ Note: This machine uses eth0
    virtual_router_id 50
    priority 90             # Lower score = Backup
    advert_int 1
    unicast_src_ip 10.0.0.16
    unicast_peer {
        10.0.0.13
    }
    authentication {
        auth_type PASS
        auth_pass 1111
    }
    virtual_ipaddress {
        10.0.0.100 dev eth0 label eth0:1
    }
    track_script {
        chk_manual
    }
}

# Instance 2: I am MASTER, claiming VIP 200
vrrp_instance VI_2 {
    state MASTER
    interface eth0
    virtual_router_id 60
    priority 100            # Higher score = Master
    advert_int 1
    unicast_src_ip 10.0.0.16
    unicast_peer {
        10.0.0.13
    }
    authentication {
        auth_type PASS
        auth_pass 2222
    }
    virtual_ipaddress {
        10.0.0.200 dev eth0 label eth0:2
    }
    track_script {
        chk_manual
    }
}
```

---

## 4. Start and Verify

### Start the Service
```bash
sudo systemctl restart keepalived
```

### Check Status
Under normal conditions:
*   **Node A** holds VIP `10.0.0.100`.
*   **Node B** holds VIP `10.0.0.200`.
*   **Both machines are active, utilizing resources efficiently!**

### 💣 Simulating a Hard Crash
I tried stopping the Keepalived service on **Node A** to simulate a server crash:

```bash
# Execute on Node A
systemctl stop keepalived
```

**The Miracle Happens:**
Checking the IP on **Node B** (`ip addr`), I found it instantly grabbed VIP `100` as well!
At this moment, Node B holds both VIPs (`100` and `200`), handling all traffic alone.

When I restarted Node A, VIP `100` automatically floated back, restoring the Active-Active state.

---

## 📝 Lessons Learned & Tips

1.  **Network Interface Names**: Always check with `ip addr`. Different machines might have different interface names (e.g., `ens33` vs `eth0`), and putting the wrong one in the config causes immediate failure.
2.  **Unicast Mode**: In cloud environments or specific networks, Multicast might be blocked. It is recommended to configure `unicast_peer` to use Unicast.
3.  **Syntax Sensitivity**: The Keepalived configuration file is very sensitive to brackets `{}` and spaces. Be careful when copy-pasting.
4.  **Troubleshooting**: When in doubt, `journalctl -u keepalived -f` is your best friend for debugging.

Keepalived combined with Nginx is a classic open-source High Availability solution. The configuration is simple, but it is incredibly stable! If you have some spare servers, give it a try!

---
*(Originally published on [1water1.top](https://1water1.top))*
```
