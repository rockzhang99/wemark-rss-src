# 云端(RSS 服务端)镜像 —— 改动036 阶段3
# 设计要点：云端数据中心 IP 永远不调用微信接口，从构建层面物理删除微信驱动代码，
# 即使误打包也会被 main.py 的运行时守卫(RuntimeError)拦截。
FROM python:3.11-slim

ENV DEPLOY_ROLE=cloud \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    TZ=Asia/Shanghai \
    INSTALL=False

WORKDIR /app

# 编译依赖（psycopg2/mysql 等可选；如使用 sqlite 可去掉 gcc/libmysql）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc default-libmysqlclient-dev pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装裁剪后的依赖（不含 playwright/selenium，不会下载 Chromium）
COPY requirements.cloud.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 仅复制云端所需源码
COPY core/ ./core/
COPY apis/ ./apis/
COPY schemas/ ./schemas/
COPY jobs/ ./jobs/
COPY web.py main.py init_sys.py ./
COPY config.example.yaml ./config.yaml
COPY static/ ./static/

# 物理删除微信驱动相关代码（构建层面锁死云端不碰微信）
# - core/wx、core/article_content：微信抓取/正文抽取
# - jobs/mps、jobs/article、jobs/failauth、jobs/fetch_no_article：微信采集任务
# - driver、views、web_ui、doc2pdf、qtserver、tools、public：本地 Agent 专属，云端不需要
RUN rm -rf core/wx core/article_content.py \
    && rm -f jobs/mps.py jobs/article.py jobs/failauth.py jobs/fetch_no_article.py \
    && rm -rf driver views web_ui doc2pdf qtserver tools public 2>/dev/null || true

EXPOSE 8001
# 云端纯 RSS 服务：不启动本地授权/定时任务，仅提供 RSS + 上传 API
CMD ["python", "main.py", "-job", "False"]
