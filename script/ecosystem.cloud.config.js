// 云端 RSS 服务端的 pm2 配置（混合架构 改动036 阶段3/手动部署）
// 用法（在仓库根目录）：
//   pm2 start script/ecosystem.cloud.config.js
//   pm2 save && pm2 startup   # 开机自启
//
// 注意：
//   - script 指向 venv 里的 python 解释器，确保用的是 requirements.cloud.txt 装的依赖；
//   - 若你的虚拟环境目录不叫 venv，请改 script 路径；
//   - 云端只跑 RSS + 上传 API，故 -job False（不启动本地授权/抓取/定时任务）。
module.exports = {
  apps: [
    {
      name: "wemark-cloud",
      // venv 里的解释器（相对 cwd）；如用绝对路径更稳，例如 /opt/wemark-cloud/venv/bin/python
      script: "venv/bin/python",
      args: "main.py -job False",
      cwd: __dirname + "/..",           // 仓库根目录（本文件在 script/ 下）
      interpreter: "none",              // 关键：让 pm2 直接执行 script，不要用 node 解释
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      max_memory_restart: "500M",
      env: {
        DEPLOY_ROLE: "cloud",           // 强制云端模式（等价于 config.yaml deploy.role=cloud）
        PYTHONUNBUFFERED: "1"           // 让日志实时刷到 pm2 log，不被缓冲
      },
      out_file: "cloud.out.log",
      error_file: "cloud.err.log",
      merge_logs: true,
      time: true                        // 日志加时间戳
    }
  ]
};
