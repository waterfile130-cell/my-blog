---
title: "🚀 Ansible 笔记： LVS+Keepalived 的高可用负载均衡集群与 Ansible 自动化运维"
summary: "本文记录了构建基于 LVS+Keepalived 的高可用负载均衡集群并结合 Ansible 实现自动化运维。"
date: 2025-12-27T18:30:18+08:00
draft: false
---

## 集群环境

| 节点名称 | IP 地址 | 操作系统 | 角色 | 关键组件 |
|---|---:|---|---|---|
| Rocky-12 | 10.0.0.12 | Rocky Linux 9.4 | LVS Master / Ansible Control | Keepalived, ipvsadm, Ansible |
| Rocky-15 | 10.0.0.15 | Rocky Linux 9.4 | LVS Backup | Keepalived, ipvsadm |
| Ubuntu-13 | 10.0.0.13 | Ubuntu 24.04 | Real Server (RS) | Nginx (Web), ARP 抑制 |
| Ubuntu-16 | 10.0.0.16 | Ubuntu 24.04 | Real Server (RS) | Nginx (Web), ARP 抑制 |

**VIP (Virtual IP)：** 10.0.0.100

## 第一阶段：Keepalived 高可用 (High Availability)

### 1.1 部署策略：RPM vs Source

为了掌握不同场景的部署能力，采用分组部署策略：

- **Rocky 组（快速交付）**：直接使用 `dnf install keepalived`，模拟企业标准化环境。
- **Ubuntu 组（深度定制）**：下载 v2.2.8 源码，手动编译安装，解决 `libssl-dev`, `libnl-3-dev` 等依赖，手动配置 Systemd 服务文件。

### 1.2 核心配置解析

采用 VRRP（虚拟路由冗余协议）实现 VIP 漂移。

- 抢占模式：Master 优先级为 100，Backup 为 90，Master 恢复后会自动抢回 VIP。
- 业务感知（Health Check）：Keepalived 本身主要检测进程/主机存活，无法直接感知业务（例如 Nginx）。常用做法是配合 `vrrp_script` 调用自定义脚本（例如 `check_nginx.sh`），当 Nginx 不可用时降低权重触发切换。

示例：`check_nginx.sh`

```bash
#!/bin/bash
if ! pgrep -x nginx >/dev/null; then
  exit 1
fi
exit 0
```

在 `keepalived.conf` 中可以通过 `vrrp_script` + `track_script` 配置权重变化。

### 1.3 故障演练（Chaos Engineering）

- 拔线测试：停止 Master 的 Keepalived 服务，VIP 秒级漂移至 Backup，业务不中断。
- 脑裂复现：通过防火墙阻断 VRRP 组播包，复现“双主”导致 IP 冲突的场景。

## 第二阶段：LVS-DR 负载均衡 (Load Balancing)

### 2.1 架构升级

由 Active-Standby 升级为 LVS-DR（Direct Routing）。流量走向：Client -> VIP -> LVS -> RS -> Client。优点是回包不经过 LVS，提高吞吐。

### 2.2 关键技术难点：ARP 抑制

在 DR 模式下，LVS 与 RS 都存在 VIP，为避免 IP 冲突，需要在 RS 上进行 ARP 抑制，并将 VIP 绑定到回环接口（lo）。常用内核参数：

```bash
# 关键内核参数（示例）
sysctl -w net.ipv4.conf.lo.arp_ignore=1
sysctl -w net.ipv4.conf.lo.arp_announce=2
sysctl -w net.ipv4.conf.all.arp_ignore=1
sysctl -w net.ipv4.conf.all.arp_announce=2
```

排错记录：Ubuntu 24.04 可能缺少 `ifconfig`（来自 `net-tools`），建议使用 `ip addr add` 或安装 `net-tools`。

### 2.3 验证技巧

- 浏览器存在长连接/缓存陷阱，刷新可能仍访问同一后端。正确办法使用 `curl` 等短连接工具进行验证，以观察轮询/调度效果。

## 第三阶段：Ansible 自动化运维 (Automation)

### 3.1 信任构建

- 在控制机（Rocky-12）生成 SSH Key（`ssh-keygen`），使用 `ssh-copy-id` 将公钥分发到被控机，建立免密连通性。

### 3.2 Playbook 实战（Infrastructure as Code）

- Inventory 分组为 `[lb]`（负载均衡）与 `[web]`（后端）。
- 使用模块化 Playbook：自动识别 `yum` / `apt`，安装软件；使用 `user`、`copy` 等模块统一管理用户和配置文件。
- 幂等性：多次执行 Playbook，系统状态保持一致，未发生配置漂移。

## 总结

本次实战搭建了一套具备高可用（HA）、高性能（LB）与可管理（Automation）特性的基础架构。解决了跨系统兼容、网络协议冲突与长连接验证等运维痛点。

--

