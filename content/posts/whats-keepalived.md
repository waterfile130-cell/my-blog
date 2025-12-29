---
title: "keepalived"
description: "keepalived基础知识"
date: 2025-12-23T10:14:01.6224284+08:00
image:
tags:
    - Linux
    - 运维
    - 高可用集群
categories:
    - Tech
draft: false


---

### 1. 什么是高可用 (High Availability, HA)？

在 IT 领域，'高可用'指的是系统在面对硬件故障、软件错误或网络问题时，仍能长时间持续提供服务的能力。

    '目标'：消除单点故障（SPOF）。如果一台服务器挂了，另一台能立马顶上。
    '衡量标准'：通常用“几个9”来衡量，比如 99.99%（意味着一年停机时间不超过 52 分钟）。

'Keepalived' 就是Linux下一个轻量级的高可用解决方案，它最初是为 LVS（Linux Virtual Server）设计的，用来管理并监控负载均衡集群中的服务节点状态。


### 2. 核心基石：VRRP 协议

要懂 Keepalived，必须先懂 'VRRP' (Virtual Router Redundancy Protocol，虚拟路由器冗余协议)。Keepalived 就是用 C 语言实现了 VRRP 协议。

#### VRRP 的工作原理：
想象一下，你有一群路由器，我们想让它们在外面看起来像'一台'超级路由器。

1.  '虚拟 IP (VIP)'：这是对外提供服务的 IP 地址。客户端只连接这个 IP，不知道后面具体是哪台机器。
2.  '角色'：
    '   'Master (主节点)'：真正持有 VIP，负责处理流量，并周期性地向 Backup 发送“我还活着”的广播包（心跳）。
    '   'Backup (备节点)'：监听 Master 的广播。
3.  '选举与故障切换 (Failover)'：
    '   Backup 如果在一定时间内（通常是3秒）收不到 Master 的心跳包，就认为 Master 挂了。
    '   Backup 根据优先级（Priority）选举出新的 Master，接管 VIP。
    '   一旦旧 Master 恢复，根据配置（抢占模式），它可能会重新夺回 VIP。


### 3. Keepalived 基础知识

Keepalived 主要有两个核心功能：

1.  'VRRP 高可用'：也就是上面说的，管理 VIP 在多台服务器之间漂移。
2.  '健康检查 (Health Checking)'：
    '   它可以检查后端真实服务器（如 Nginx、MySQL）是否活着。
    '   'Layer 3 (IP层)'：通过 ICMP (Ping) 检查。
    '   'Layer 4 (TCP端口层)'：检查端口（如 80, 3306）是否通。
    '   'Layer 7 (应用层)'：通过自定义脚本检查服务状态（比如 Nginx 进程还在，但网页返回 500 错误）。

'Keepalived 的组件结构'：
    '   'Checkers'：负责真实服务器的健康检查。
    '   'VRRP Stack'：处理 VRRP 协议的广播和选举。
    '   'Netlink Reflector'：与 Linux 内核交互，负责在网卡上添加或删除 VIP。


### 4. 缺省路由 (Default Route) 与 Keepalived

'角度一：客户端/下游设备的缺省网关'
    '   '场景'：Keepalived 用在路由器或防火墙的高可用上。
    '   '作用'：局域网内的电脑需要上网，它们的'缺省路由（网关）'指向的是 VRRP 生成的 'VIP'。
    '   '效果'：当主路由器挂掉，VIP 漂移到备用路由器，局域网内的电脑无感知，依然通过 VIP 上网。

'角度二：服务器本身的路由'
    '   '场景'：Keepalived 部署在服务器上（如 Nginx 负载均衡）。
    '   '问题'：Keepalived 配置文件中有一个 `virtual_routes` 区块。
    '   '作用'：当这台机器变成 Master 时，可以自动添加一条路由规则；当它变成 Backup 时，自动删除。
    '   '实战'：通常在服务器模式下我们很少配 `virtual_routes`，只配 `virtual_ipaddress` 就够了。但在复杂的双网卡、跨网段环境中，可能需要用它来指定回包的路由。


### 5. 高可用方式 (HA Modes)

Keepalived 常见的架构模式主要有两种：

#### 模式一：主备模式 (Active-Standby) —— 最常用、最简单
    '   '架构'：节点 A (Master) + 节点 B (Backup)。
    '   'VIP'：只有 1 个 VIP。
    '   '状态'：
    '       正常时：VIP 在节点 A 上，所有流量只走 A。节点 B 闲置（作为冷备）。
    '       故障时：VIP 漂移到 B，流量走 B。
    '   '优点'：配置简单，极少出现数据不一致。
    '   ''缺点''：浪费了一台服务器的资源（节点 B 平时没事干）。

#### 模式二：双主模式 (Active-Active) / 双主双备
    '   ''架构''：节点 A + 节点 B。
    '   ''VIP''：配置 ''2 个 VIP'' (VIP1, VIP2)。
    '   ''配置逻辑''：
        '   对于 VIP1：节点 A 是 Master，节点 B 是 Backup。
        '   对于 VIP2：节点 B 是 Master，节点 A 是 Backup。
    '   ''流量分配''：通过 DNS 轮询，将一半用户解析到 VIP1，一半解析到 VIP2。
    '   ''状态''：两台机器同时工作。如果 A 挂了，VIP1 跑到 B 上，此时 B 拥有两个 VIP，承担所有流量。
    '   ''优点''：资源利用率高。


### 6. 实战配置示例 (主备模式)

假设我们要对两台 Nginx 负载均衡器做高可用。
    '   Master IP: 192.168.1.10
    '   Backup IP: 192.168.1.11
    '   ''VIP: 192.168.1.100''

#### A. Master 节点配置 (`/etc/keepalived/keepalived.conf`)

```nginx
global_defs {
   router_id LVS_DEVEL_MASTER  # 标识本节点的ID，随便写但要唯一
}

# 定义一个检测脚本，用来检查 Nginx 是否活着
vrrp_script check_nginx {
    script "/etc/keepalived/check_nginx.sh"
    interval 2  # 每2秒检测一次
    weight -20  # 如果检测失败，权重减少20
}

vrrp_instance VI_1 {
    state MASTER          # 初始状态：Master
    interface eth0        # 绑定VIP的网卡
    virtual_router_id 51  # VRID，主备必须一致！
    priority 100          # 优先级，Master要比Backup高
    advert_int 1          # 广播间隔1秒

    authentication {
        auth_type PASS
        auth_pass 1111    # 密码，主备必须一致
    }

    virtual_ipaddress {
        192.168.1.100     #这就是 VIP
    }

    track_script {
        check_nginx       # 调用上面的检测脚本
    }
}
```

#### B. Backup 节点配置

```nginx
global_defs {
   router_id LVS_DEVEL_BACKUP
}

vrrp_script check_nginx {
    script "/etc/keepalived/check_nginx.sh"
    interval 2
    weight -20
}

vrrp_instance VI_1 {
    state BACKUP          # 初始状态：Backup
    interface eth0
    virtual_router_id 51  # 必须和Master一样
    priority 90           # 优先级必须比Master低
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass 1111
    }

    virtual_ipaddress {
        192.168.1.100
    }

    track_script {
        check_nginx
    }
}
```

#### C. 关键点：健康检测脚本
Keepalived 进程活着不代表业务活着。如果 Nginx 挂了，Keepalived 还在，VIP 就不会漂移，用户访问就会报错。所以必须配合脚本：

脚本逻辑：'如果 Nginx 进程不存在，就尝试重启 Nginx；如果还不行，就杀掉 Keepalived 进程（或者降低权重），触发 VIP 漂移。'

### 7. 常见问题：脑裂 (Split Brain)

''什么是脑裂？''
主备之间的心跳线断了（比如防火墙挡住了 VRRP 组播包，或者网线断了），Backup 以为 Master 死了，于是强行接管 VIP。结果是：''Master 和 Backup 都有 VIP''。

''后果''：
IP 冲突，数据写入混乱，用户访问时通时断。

''如何预防？''
1.  防火墙允许 VRRP 协议（IP 协议号 112）通过。
2.  使用串行电缆或多条线路做心跳冗余。
3.  脚本检测：一旦发现自己是 Master 但 Ping 不通网关，自动降级。

### 总结

    '   ''Keepalived'' = ''VRRP'' (抢 VIP) + ''Health Check'' (看病)。
    '   ''VRRP'' 让多台机器共享一个 ''VIP''，谁优先级高谁拿。
    '   ''缺省路由'' 在这里通常指客户端将 VIP 作为网关，或者 Keepalived 自身管理路由表。
    '   最稳的架构是 ''主备模式 (Master/Backup)''。
    '   一定要配置 '健康检测脚本'，确保应用挂了 VIP 能及时切换。
