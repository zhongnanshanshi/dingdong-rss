# 叮咚FM《以案说法》非官方播客 RSS

基于已观察到的 2026-10-23 与 2026-10-24 音频文件命名规律，尝试发现新节目。不是官方接口，命名变化会导致停止更新。

## 部署

1. 注册/登录 GitHub，新建 **Public** 仓库，例如 `dingdong-rss`。
2. 上传本压缩包里的所有内容到仓库根目录，**包括 `.github/workflows/rss.yml` 隐藏目录**。最方便的方式是在电脑解压后通过 GitHub 的 Upload files 上传，确认目录结构保留。
3. 仓库 Settings → Actions → General → Workflow permissions：选择 **Read and write permissions**，保存。
4. 仓库 Settings → Pages → Build and deployment → Source：选择 **GitHub Actions**。
5. Actions → Update podcast RSS → Run workflow。初次运行可能需要数分钟；会尝试最多 3 期。后续每天自动执行。
6. RSS 地址为 `https://你的用户名.github.io/dingdong-rss/feed.xml`（仓库名称不同则相应替换）。等待 Pages 部署完成后，在 AntennaPod 添加 RSS URL。

## 重要限制

- 当前未在 GitHub Actions 实际测试；需要先确认 Actions 可访问阿里云 OSS 的 m3u8 和 ts 文件。
- GitHub Releases 保存 MP3，GitHub Pages 仅保存 RSS。公开仓库的 Release 音频可被公众访问；请先确认内容使用及再分发许可。若没有授权，不应公开再托管节目音频。
- 文件大小、流量和 Actions 用量均受 GitHub 相关政策与配额约束。每天运行会尝试最多 3 个新节目，历史回补窗口为 15 天，可能无法覆盖更早节目。
- RSS 中的 `enclosure` 需要 MP3 实际长度，程序从 GitHub Release 读取；若读取失败则长度为 0，部分播客客户端可能不兼容。
- 文件名日期规律只由两期样本推断，不保证持续有效。程序检查播放列表是否存在。
- GitHub Pages 项目 URL 跟随 GitHub 用户名和仓库名；请不要在部署完成前将示例 URL 当作真实可用订阅源。
