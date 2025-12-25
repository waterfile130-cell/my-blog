---

# 🚀 Ansible 实战笔记：构建自动化运维集群（Nginx + HAProxy + Roles）

> **摘要**：本文记录了我从零开始学习 Ansible 的完整过程。在一个由 Rocky Linux 和 Ubuntu 组成的混合环境中，实现了 SSH 免密互信、Nginx 批量部署、差异化配置自动分发、HAProxy 负载均衡集群搭建，以及使用 Roles 重构代码和 Vault 加密敏感数据。

---

## 1. 实验环境规划

我使用了 3 台虚拟机，操作系统涵盖了 RHEL 系和 Debian 系，以测试 Ansible 对异构系统的兼容性。

| 主机名 | IP 地址 | 角色 | 操作系统 | 备注 |
| :--- | :--- | :--- | :--- | :--- |
| **Rocky-12** | `10.0.0.12` | **控制节点 (Ansible Server)**<br>负载均衡器 (HAProxy) | Rocky Linux 9 | **指挥官**，所有命令在此执行 |
| **Ubuntu-13** | `10.0.0.13` | 被控节点 (Web Server) | Ubuntu 24.04 | 运行 Nginx |
| **Ubuntu-16** | `10.0.0.16` | 被控节点 (Web Server) | Ubuntu 24.04 | 运行 Nginx |

---

## 2. 基础环境配置 (The Foundation)

### 2.1 安装 Ansible
Ansible 是无代理（Agentless）的，只需要在控制节点安装即可。

```bash
# 在 Rocky 9 控制节点上
sudo dnf install epel-release -y
sudo dnf install ansible -y
```

### 2.2 SSH 免密互信 (踩坑记录)
这是 Ansible 通信的基础。
*   **踩坑：** 一开始使用了 `ssh-keygen -p` 导致报错，后来发现小写 `-p` 是修改密码，大写 `-P` 才是设置新密码（空密码）。

**正确操作：**
```bash
# 1. 生成密钥 (一路回车)
ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa

# 2. 分发公钥到所有节点 (包括自己)
ssh-copy-id root@10.0.0.12
ssh-copy-id root@10.0.0.13
ssh-copy-id root@10.0.0.16
```

### 2.3 构建 Inventory (花名册)
为了不污染系统配置，我在项目目录建立了独立的配置文件。

**文件结构：** `/root/ansible_start/`
*   **`hosts` (清单文件):**
    ```ini
    [web]
    10.0.0.13
    10.0.0.16
    
    [lb]
    10.0.0.12
    ```
*   **`ansible.cfg` (配置文件):**
    ```ini
    [defaults]
    inventory = ./hosts
    host_key_checking = False  # 关键配置：跳过 SSH 指纹验证
    ```

---

## 3. Ad-Hoc 命令体验

在写剧本前，先用单行命令测试连接。

*   **连通性测试：**
    ```bash
    ansible all -m ping
    ```
*   **跨平台安装软件 (混合双打)：**
    使用 `package` 模块，它会自动判断是 `apt` 还是 `yum/dnf`。
    ```bash
    # 批量安装 git
    ansible web -m package -a "name=git state=present"
    ```

---

## 4. Playbook 实战：Nginx 差异化部署

我编写了一个剧本，不仅安装 Nginx，还利用 **Jinja2 模板**实现了“千人千面”的网页效果。

### 4.1 编写模板 (`templates/index.html.j2`)
```html
<html>
<body>
    <h1>部署成功!</h1>
    <!-- 自动填入当前机器的主机名 -->
    <p>我是主机: {{ ansible_hostname }}</p>
    <p>系统: {{ ansible_os_family }}</p>
</body>
</html>
```

### 4.2 编写剧本 (`deploy.yml`)
这里处理了一个难点：Ubuntu 和 Rocky 的 Nginx 默认网页路径不同。我使用了 `when` 条件判断。

```yaml
---
- name: 部署 Nginx
  hosts: web
  tasks:
    - name: 安装 Nginx
      package: name=nginx state=present

    - name: 发布首页 (Ubuntu)
      template:
        src: templates/index.html.j2
        dest: /var/www/html/index.html
      when: ansible_os_family == "Debian"

    - name: 发布首页 (Rocky)
      template:
        src: templates/index.html.j2
        dest: /usr/share/nginx/html/index.html
      when: ansible_os_family == "RedHat"
      
    - name: 启动服务
      service: name=nginx state=started enabled=yes
```

---

## 5. 进阶挑战：HAProxy 负载均衡集群

这是本次实验最高光的时刻。我将控制节点（Rocky-12）配置为负载均衡器，自动分发流量给后端的 Web 服务器。

### 5.1 动态配置模板
难点在于不能把后端 IP 写死。我使用了 Jinja2 的 `for` 循环遍历 `[web]` 组。

**文件：`templates/haproxy.cfg.j2` (核心片段)**
```jinja2
backend app_servers
    balance roundrobin
    # 自动遍历 inventory 中的 web 组
    {% for host in groups['web'] %}
    server {{ host }} {{ host }}:80 check
    {% endfor %}
```

### 5.2 效果验证
部署完成后，访问负载均衡器端口，实现了轮询效果：
```bash
curl http://10.0.0.12:8080
# 第一次返回：我是主机: ubuntu-13
# 第二次返回：我是主机: ubuntu-16
```

---

## 6. 架构重构：使用 Roles (角色)

随着 `yml` 文件越来越多，管理变得混乱。我使用 Ansible Roles 进行了重构。

**操作步骤：**
1.  **初始化：** `ansible-galaxy init nginx`
2.  **拆解：**
    *   将 tasks 移动到 `roles/nginx/tasks/main.yml`
    *   将 templates 移动到 `roles/nginx/templates/`
    *   将 handlers 移动到 `roles/nginx/handlers/main.yml`
3.  **主入口 (`site.yml`):**
    ```yaml
    ---
    - hosts: web
      roles:
        - nginx
    ```

**心得：** 重构后的代码结构清晰，就像把散乱的衣服整理进了收纳柜，非常适合大规模维护。

---

## 7. 安全加固：Ansible Vault

为了不让管理员密码明文暴露，我学习了加密功能。

1.  **创建加密柜：**
    ```bash
    ansible-vault create secrets.yml
    # 输入密码：123456
    # 内容：admin_pass: "MySecretP@ssword"
    ```
2.  **使用加密变量：**
    在 playbook 中加载 `vars_files: secrets.yml`。
3.  **执行：**
    ```bash
    ansible-playbook create_user.yml --ask-vault-pass
    ```

---

## 8. 常见报错与排查 (Troubleshooting)

在学习过程中遇到的几个典型报错，非常具有参考价值：

1.  **[WARNING]: provided hosts list is empty**
    *   **原因：** 在非项目目录下执行了 `ansible` 命令，导致读不到 `hosts` 文件。
    *   **解决：** 必须进入 `ansible.cfg` 所在的目录操作。
2.  **Syntax Error while loading YAML**
    *   **原因：** 复制粘贴代码时，缩进错误，或者文件开头多写了 `---`。
    *   **解决：** YAML 对缩进极其敏感，务必对齐；使用 `--syntax-check` 参数预检。
3.  **Command not found (curl)**
    *   **原因：** 最小化安装的 Ubuntu 缺少 `curl` 命令。
    *   **解决：** 使用 Ansible 批量补装：`ansible web -m package -a "name=curl state=present"`。

---

## 结语

通过这次实战，我深刻理解了 Ansible **"约定大于配置"** 的设计哲学。从简单的命令执行，到复杂的集群编排，Ansible 极大地释放了运维的生产力。
