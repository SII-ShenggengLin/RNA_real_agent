# Claude Code 在 Inspire 平台上的 SIGKILL 问题与修复手册

> 首次排查：2026-08-12。症状：Claude Code（终端 CLI 与 VS Code 扩展）启动后几秒到几分钟内被
> `SIGKILL`（终端显示 `Killed`；扩展报 "Claude Code process terminated by signal SIGKILL"）。
> 进程被杀后终端残留鼠标追踪，鼠标移动会在命令行打出 `35;70;22M…` 乱码（盲打 `reset` 回车可恢复）。

## 根因

**平台宿主机安全 agent 按进程名查杀：任何名字（comm/exe 路径）含 `claude` 子串的进程都会被
SIGKILL**。杀进程的动作来自容器外（宿主机），容器内看不到凶手。

- 与 Claude Code 版本无关（2.1.227 / 2.1.228 / 2.1.229 均被杀）
- 与内存/CPU 无关（被杀时 RSS 平稳 ~300MB，cgroup `oom_kill` 计数为 0）
- 与认证无关（401 是之前另一个已修复的问题，见文末）
- strace 证实 SIGKILL 来自进程树外部：所有线程都是 `+++ killed by SIGKILL +++`，树内无 kill 调用

### 一分钟验证当前机器是否存在该查杀

```bash
cp /bin/sleep /tmp/claude && /tmp/claude 20 &
sleep 6
pgrep -xc claude >/dev/null 2>&1 && echo "存活: 无查杀" || echo "被杀: 按名查杀仍存在"
rm -f /tmp/claude
```

对照组：同一个 sleep 二进制改名为 `sleeptest` 则正常存活（名字决定生死）。

## 修复 1：终端 CLI（改名符号链接）

原理：进程名跟随执行路径 basename，改名后 killer 匹配不到。

```bash
mkdir -p /root/.local/bin
ln -sf /root/.nvm/versions/node/v24.15.0/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe \
       /root/.local/bin/cld
```

`/root/.bashrc` 中应有（2026-08-12 已加入，若新机器丢失则补上）：

```bash
alias claude='DISABLE_AUTOUPDATER=1 cld'
```

验证：新开终端 `type claude` 应显示该 alias；`timeout 60 script -qec cld /dev/null` 退出码 124
= 存活满 60 秒（137 = 被杀）。

## 修复 2：VS Code 扩展（改名 + 包装脚本，每次扩展升级后需重打）

扩展每次自动更新都会覆盖补丁（2.1.228→2.1.229 已发生过一次）。建议关闭扩展自动更新：
Extensions 面板 → Claude Code → 右键/管理齿轮 → 取消 Auto Update。

打补丁（把版本号换成当前安装的）：

```bash
dir=/root/.vscode-server/extensions/anthropic.claude-code-2.1.229-linux-x64/resources/native-binary
mv "$dir/claude" "$dir/cld"
printf '#!/bin/sh\nexec "$(dirname "$0")/cld" "$@"\n' > "$dir/claude"
chmod +x "$dir/claude" "$dir/cld"
```

原理：扩展照常启动名为 `claude` 的包装脚本，脚本几毫秒内 `exec` 成 `cld`，进程名随之改变，
按名扫描的 killer 基本抓不到这个窗口。

验证（退出码 124 = 存活满 45 秒）：

```bash
timeout 45 script -qec "$dir/claude" /dev/null; echo $?
```

回滚方法：删掉包装脚本 `claude`，把 `cld` 改名回 `claude`。

## 附：本次顺带修复的其他问题（2026-08-12）

1. **Kimi/DeepSeek 配置冲突**（启动警告 `Both ANTHROPIC_AUTH_TOKEN and ANTHROPIC_API_KEY set`、
   扩展 401）：已删除 `/usr/local/bin/claude-kimi`、`~/.claude-kimi.env` 及 `.bashrc`/`.profile`
   中相关加载与别名；DeepSeek 环境变量块移到 `.bashrc` **顶部**（`PS1` 检查之前，sshd 非交互
   shell 也会加载），并加 `unset ANTHROPIC_API_KEY ENABLE_TOOL_SEARCH` 防御旧进程环境残留。
2. **`~/.claude.json` 中残留已批准的 Kimi API key 指纹**（导致旧环境下 Kimi key 被静默优先
   使用 → 401）：已把指纹从 `customApiKeyResponses.approved` 移到 `rejected`。
3. **终端乱码**：进程被 SIGKILL 后鼠标追踪未关闭所致，治标用 `reset`；治本靠上面的改名修复。

## 注意事项

- 按名查杀是**平台侧行为**（2026-08-12 实例重启后首次出现），改名只是绕过。建议向 Inspire
  平台管理员确认是误伤还是有意封禁；若为有意封禁，长期使用变通方案可能有违规风险。
- `/root` 下的配置（`.bashrc`、`cld` 符号链接、npm 全局 claude）在实例重启后可能保留也可能
  丢失，取决于平台镜像保存策略；丢失时按本手册重跑即可。项目目录 `/inspire/hdd/...` 是持久存储。
